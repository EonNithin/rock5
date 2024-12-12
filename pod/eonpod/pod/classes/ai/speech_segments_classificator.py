import statistics
from collections import namedtuple
from pod.classes.ai.similarity_estimator import SimilarityEstimator
from pod.classes.ai.speech_segment import SpeechSegment
from pod.classes.ai.semantic_sentences_groupper import SemanticSentencesGroupper
from pod.classes.ai.gpt_speech_segments_classificator import GPTSpeechSegmentsClassificator
from pod.classes.ai.logging_service import logger

SILENCE_THRESHOLD_SEC = 5
MIN_DURATION_SEC = 10
RELEVANCE_THRESHOLD = 0.5

SemanticCluster = namedtuple("SemanticCluster", ["id", "text", "relevance_score"])


class SpeechSegmentsClassificator:
    def __init__(
        self, speech_segments: list, class_number: str, subject_name: str, use_gpt: bool, syllabus: str, input_folder: str
    ) -> None:
        self.__class_number = class_number
        self.__subject_name = subject_name
        self.__speech_segments = speech_segments
        self.__full_text = self.__generate_full_text()
        self.__syllabus = syllabus
        self.__use_gpt = use_gpt
        self.__input_folder = input_folder
        pass

    def get_subject_sample_text(self, video_num: int):
        input_json_path = f"../downloads/videos/video{video_num}/subject_text.txt"
        with open(input_json_path) as f:
            return f.read()

    def classify(self) -> list:
        logger.info("Classifying speech segments...")
        logger.info(f"USE_GPT: {self.__use_gpt}")

        try:
            if self.__use_gpt:
                self.__classify_with_gpt()
                for segment in self.__speech_segments:
                    print(
                        f"{segment.is_relevant}: {segment.start_time_string}: {segment.end_time_string} {segment.text}\n"
                    )
                merged_speech_segments = self.__merge_speech_segments()

                for segment in merged_speech_segments:
                    print(
                        f"{segment.is_relevant}: {segment.start_time_string}: {segment.end_time_string} {segment.text}\n"
                    )
                
                # self.__classify_per_syllabus(merged_speech_segments)

                return merged_speech_segments
        except Exception as e:
            logger.error(f"Error while classifying with GPT: {e}")
            raise


        sim_estimator = SimilarityEstimator(self.__full_text)

        # calculate each segment similarity to the whole text
        for segment in self.__speech_segments:
            segment.relevance_score = sim_estimator.calculate_similarity(segment.text)

        clusters = self.__cluster_full_text(sim_estimator)
        self.__map_speech_segments_2_clusters(clusters)
        self.__speech_segments = self.__merge_segments_by_clusters()

        # set segments relevancy based on the average similarity
        for segment in self.__speech_segments:
            segment.is_relevant = (
                segment.relevance_score >= RELEVANCE_THRESHOLD
                or segment.cluster_relevance_score >= RELEVANCE_THRESHOLD
            )

        merged_speech_segments = self.__merge_speech_segments()

        return merged_speech_segments

    def __classify_with_gpt(self):
        gpt_classificator = GPTSpeechSegmentsClassificator(input_folder = self.__input_folder)
        gpt_classificator.classify(
            self.__speech_segments, self.__class_number, self.__subject_name, self.__syllabus
        )
        for segment in self.__speech_segments:
            segment.is_relevant = segment.relevance_score_gpt >= RELEVANCE_THRESHOLD

    def __classify_per_syllabus(self, speech_segments: list):
        logger.info("Classifying per syllabus...")
        logger.info("Currently CBSE is supported only")
        logger.info(f"USE_GPT: {self.__use_gpt}")
        if not self.__use_gpt:
            logger.warning("Classification per Syllabus is only supported with GPT")
            return

        gpt_classificator = GPTSpeechSegmentsClassificator(input_folder = self.__input_folder)
        gpt_classificator.classify_per_CBSE(speech_segments, self.__class_number, self.__subject_name, self.__syllabus)

    def __merge_segments_by_clusters(self) -> list:
        # array or arrays
        arr = []
        arr2 = []
        cluster_id = None
        for segment in self.__speech_segments:
            if cluster_id is None:
                cluster_id = segment.cluster_id
                arr2.append(segment)
            else:
                if cluster_id != segment.cluster_id:
                    arr.append(arr2)
                    arr2 = []
                    cluster_id = segment.cluster_id
                arr2.append(segment)
        # add the last one
        arr.append(arr2)

        res = []
        for arr2 in arr:
            new_segment = SpeechSegment()
            new_segment.text = ""
            new_segment.start_time_sec = arr2[0].start_time_sec
            new_segment.end_time_sec = arr2[-1].end_time_sec
            new_segment.cluster_id = arr2[0].cluster_id
            new_segment.cluster_relevance_score = arr2[0].cluster_relevance_score

            max_relevance_score = 0

            for segment in arr2:
                new_segment.text += " " + segment.text.strip()
                if segment.relevance_score > max_relevance_score:
                    max_relevance_score = segment.relevance_score

            new_segment.relevance_score = max_relevance_score

            res.append(new_segment)

        return res

    def __generate_full_text(self) -> str:
        full_text = ""
        for segment in self.__speech_segments:
            full_text += " " + segment.text.strip()
        return full_text

    def __cluster_full_text(self, sim_estimator: SimilarityEstimator) -> list:
        semantic_sentences_groupper = SemanticSentencesGroupper(self.__full_text)
        clusters = semantic_sentences_groupper.group()

        res = []

        for i, cluster in enumerate(clusters):
            str = ""
            for sentence in cluster:
                str += sentence

            relevance_score = sim_estimator.calculate_similarity(str)

            res.append(
                SemanticCluster(
                    id=i,
                    text=str,
                    relevance_score=relevance_score,
                )
            )

        return res

    def __merge_speech_segments(self) -> list:
        arr2 = self.__speech_segments
        while True:
            made_changes = False
            # Step 1: Merge near similar by relevancy segments
            arr1 = []
            i = 0
            while i < len(arr2):
                s_prev = arr1.pop() if len(arr1) > 0 else None
                s = arr2[i]

                if s_prev is None:
                    arr1.append(s)
                elif (
                    s_prev.is_relevant == s.is_relevant
                    and s.start_time_sec - s_prev.end_time_sec < SILENCE_THRESHOLD_SEC
                ):
                    arr1.append(
                        self.__merge_2_speech_segments(s_prev, s, s_prev.is_relevant)
                    )
                    made_changes = True
                else:
                    arr1.append(s_prev)
                    arr1.append(s)

                i += 1

            # Step 2: Merge near short segments
            i = 0
            arr2 = []
            while i < len(arr1):
                s_prev = arr2.pop() if len(arr2) > 0 else None
                s = arr1[i]

                if s_prev is None:
                    arr2.append(s)
                elif (
                    s.duration_sec < MIN_DURATION_SEC
                    and s.start_time_sec - s_prev.end_time_sec < SILENCE_THRESHOLD_SEC
                ):
                    arr2.append(
                        self.__merge_2_speech_segments(s_prev, s, s_prev.is_relevant)
                    )
                    made_changes = True
                elif (
                    s_prev.duration_sec < MIN_DURATION_SEC
                    and s.start_time_sec - s_prev.end_time_sec < SILENCE_THRESHOLD_SEC
                ):
                    arr2.append(
                        self.__merge_2_speech_segments(s_prev, s, s.is_relevant)
                    )
                    made_changes = True
                else:
                    arr2.append(s_prev)
                    arr2.append(s)

                i += 1
            if not made_changes:
                break

        return arr2

    def __merge_2_speech_segments(
        self, segment1, segment2, is_relevant: bool = True
    ) -> SpeechSegment:
        new_segment = SpeechSegment()
        new_segment.start_time_sec = segment1.start_time_sec
        new_segment.end_time_sec = segment2.end_time_sec
        new_segment.is_relevant = is_relevant
        # Calculate the weighted relevance score based on text length
        length1 = len(segment1.text) if segment1.text else 0
        length2 = len(segment2.text) if segment2.text else 0
        total_length = length1 + length2
        if total_length > 0:
            new_segment.relevance_score = (((segment1.relevance_score or 0) * length1) + ((segment2.relevance_score or 0) * length2)) / total_length
        else:
            new_segment.relevance_score = 0
        # new_segment.relevance_score = (
        #     (segment1.relevance_score or 0) + (segment2.relevance_score or 0)
        # ) / 2
        new_segment.cluster_relevance_score = max(
            segment1.cluster_relevance_score or 0, segment2.cluster_relevance_score or 0
        )
        new_segment.text = segment1.text + " " + segment2.text
        return new_segment

    def __map_speech_segments_2_clusters(self, semantic_clusters: list):
        # Cluster - text, can contain several sentences
        # Speech segments < than cluster text

        i = 0
        j = 0
        while i < len(self.__speech_segments) and j < len(semantic_clusters):
            segment = self.__speech_segments[i]
            cluster = semantic_clusters[j]

            segment_text = segment.text.strip()
            cluster_text = cluster.text.strip()

            if segment_text != cluster_text:
                if segment_text in cluster_text:
                    segment.cluster_id = cluster.id
                    segment.cluster_relevance_score = cluster.relevance_score
                    i += 1
                else:
                    j += 1
            else:
                segment.cluster_id = cluster.id
                segment.cluster_relevance_score = cluster.relevance_score
                i += 1
                j += 1
