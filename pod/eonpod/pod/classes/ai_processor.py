import os
import json
import moviepy.editor as mp
import whisper_timestamped as whisper
# from whisper_cpp_python import whisper
from pod.classes.ai.whisper_segments_processor import WhisperSegmentsProcessor
from pod.classes.ai.speech_segments_classificator import SpeechSegmentsClassificator
from pod.classes.ai.video_cutter import VideoCutter
from pod.classes.ai.logging_service import logger
from faster_whisper import WhisperModel

def get_file_name_wo_extension(file_name: str) -> str:
    return os.path.splitext(file_name)[0]


def get_output_dir(file_path: str) -> str:
    return os.path.dirname(file_path)


class ProcessVideoService:
    __whisper_model = whisper.load_model("small")

    model = WhisperModel("small", device="cpu", compute_type="float32",cpu_threads=2)

    def __init__(
        self,
        input_video_path: str,
        class_number: str,
        subject: str,
        use_gpt: bool,
        syllabus: str,
        regenerate_audio: bool = True,
        regenerate_transcription: bool = True,
        write_final_video: bool = True,
    ) -> None:
        self.__input_video_path = input_video_path
        self.__output_dir = get_output_dir(self.__input_video_path)
        self.__class_number = class_number
        self.__subject = subject
        self.__use_gpt = use_gpt
        self.__audio_file_path = None
        self.__transciption_json_file_path = None
        self.__regenerate_audio = regenerate_audio
        self.__regenerate_transcription = regenerate_transcription
        self.__write_final_video = write_final_video
        self.__transcription_json = None
        self.__speech_segments = None
        self.__classified_speech_segments = None
        self.__syllabus = syllabus

    def process(self):
        logger.info(f"start processing video path: {self.__input_video_path}")
        logger.info(f"CLASS_NUMBER: {self.__class_number}")
        logger.info(f"SUBJECT: {self.__subject}")
        logger.info(f"REGENERATE_AUDIO: {self.__regenerate_audio}")
        logger.info(f"REGENERATE_TRANSCRIPTION: {self.__regenerate_transcription}")
        logger.info(f"WRITE_FINAL_VIDEO: {self.__write_final_video}")

        # extract audio from video
        logger.info("extract audio from video: started")
        self.__extract_audio()
        logger.info("extract audio from video: done")

        # extract text from audio
        logger.info("extract transcription from audio: started")
        self.__transcription_json = self.__transcribe_audio()
        self.__speech_segments = self.__transcription_json_2_speech_segments()
        for segment in self.__speech_segments:
            print(f"{segment.is_relevant}: {segment.text}")
        logger.info("extract transcription from audio: done")

        logger.info("classify speech segments: started")
        self.__classified_speech_segments = self.__classify_speech_segments()
        self.__save_classified_speech_segments()
        logger.info("classify speech segments: done")

        # write final video
        if self.__write_final_video:
            logger.info("write final video: started")
            self.__render_final_video()
            logger.info("write final video: done")
        else:
            logger.info("write final video: skipped")

        # completed
        logger.info("process video: done")

    def __save_classified_speech_segments(self):
        relevant_transcript = ""
        str = ""
        self.transcription_text_file = os.path.join(
            self.__output_dir,
            f"{os.path.basename(self.__output_dir)}_transcript.txt"
        )
        prev_end_time_sec = None
        for i, segment in enumerate(self.__classified_speech_segments):
            if prev_end_time_sec is None:
                prev_end_time_sec = segment.end_time_sec
            else:
                str += "PAUSE: {:.2f} seconds\n".format(
                    segment.start_time_sec - prev_end_time_sec
                )
                prev_end_time_sec = segment.end_time_sec

            format_string = "{}: {} | per syllabus: {} | start: {} | end: {} | text: {}\n"
            str += format_string.format(
                i,
                'RELEVANT' if segment.is_relevant else 'OFF-TOPIC',
                segment.syllabus_classification or 'N/A',
                segment.start_time_string,
                segment.end_time_string,
                segment.text
            )
            if segment.is_relevant:
                relevant_transcript += segment.text

        with open(
            os.path.join(self.__output_dir, "classified_speech_segments.txt"), "w"
        ) as f:
            f.write(str)
        with open(self.transcription_text_file, "w") as txt_file:
                    txt_file.write(relevant_transcript)

    def __render_final_video(self):
        vc = VideoCutter(
            input_video_path=self.__input_video_path,
            output_video_path=os.path.join(self.__output_dir),
            transition_video_path=None,
            speech_segments=self.__classified_speech_segments,
        )
        logger.info(self.__classified_speech_segments)

        vc.cut()

    def __classify_speech_segments(self) -> list:
        classificator = SpeechSegmentsClassificator(
            self.__speech_segments,
            self.__class_number,
            self.__subject,
            self.__use_gpt,
            self.__syllabus,
            self.__output_dir
        )
        return classificator.classify()

    def __extract_audio(self):
        # get video file name
        video_file_name = os.path.basename(self.__input_video_path)
        # trim extension
        video_file_name = get_file_name_wo_extension(video_file_name)
        # combine path and filename
        self.__audio_file_path = os.path.join(
            os.path.dirname(self.__input_video_path),
            video_file_name + ".mp3",
        )
        logger.debug(f"audio file path: {self.__audio_file_path}")
        # write audio
        if self.__regenerate_audio or not os.path.exists(self.__audio_file_path):
            clip = None
            # open video
            try:
                clip = mp.VideoFileClip(self.__input_video_path)
            except Exception as e:
                logger.error(
                    f"problem with opening video: {self.__input_video_path}\nerror: {e}"
                )
                raise e
            # write audio
            # create a folder if it doesn't exist
            os.makedirs(os.path.dirname(self.__audio_file_path), exist_ok=True)
            try:
                clip.audio.write_audiofile(self.__audio_file_path, codec="libmp3lame")
            except Exception as e:
                logger.error(
                    f"problem with extracting audio: {self.__audio_file_path}\nerror: {e}"
                )
                raise e
        else:
            logger.debug(
                f"audio file already exists: {self.__audio_file_path}\nskipping audio extraction"
            )

    

    def __transcribe_audio(self) -> dict:
        if not self.__audio_file_path:
            logger.error("Audio file path not found.")
            raise FileNotFoundError("Audio file path not found.")

        # Define output paths for JSON and text transcription files
        self.__transcription_json_file_path = os.path.join(
            self.__output_dir,
            "whisper_transcription.json"
        )

        # Initialize transcription variable
        transcription = None

        # Only regenerate transcription if required
        if self.__regenerate_transcription or not os.path.exists(self.__transcription_json_file_path):
            try:
                # Perform transcription
                segments, info = ProcessVideoService.model.transcribe(
                    self.__audio_file_path,
                    task="translate",
                    beam_size=2,
                    word_timestamps=True,
                    language="en"
                )

                # Prepare transcription output data
                output_data = {"segments": [], "text": ""}
                text = ""

                for i, segment in enumerate(segments):
                    text += segment.text
                    segment_data = {
                        "id": i,
                        "seek": segment.seek,
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text,
                        "tokens": segment.tokens,
                        "temperature": segment.temperature,
                        "avg_logprob": segment.avg_logprob,
                        "compression_ratio": segment.compression_ratio,
                        "no_speech_prob": segment.no_speech_prob,
                        "words": [
                            {
                                "word": word.word,
                                "start": word.start,
                                "end": word.end,
                                "probability": word.probability
                            } for word in segment.words
                        ]
                    }
                    output_data["segments"].append(segment_data)

                output_data["text"] = text

                # Save the transcription to JSON and text files
                with open(self.__transcription_json_file_path, "w") as json_file:
                    json.dump(output_data, json_file, indent=4)

            except Exception as e:
                logger.error(f"Error during transcription: {self.__audio_file_path}\nError: {e}")
                raise RuntimeError(f"Transcription failed for {self.__audio_file_path}") from e

        else:
            logger.debug(
                f"Transcription file already exists: {self.__transcription_json_file_path}\nSkipping transcription extraction."
            )

        # Load the transcription data from JSON file
        with open(self.__transcription_json_file_path) as json_file:
            transcription = json.load(json_file)

        logger.debug("Transcription loaded from file.")
        return transcription

    def __transcription_json_2_speech_segments(self) -> list:
        wsp = WhisperSegmentsProcessor(segments=self.__transcription_json)
        return wsp.get_speech_segments()
