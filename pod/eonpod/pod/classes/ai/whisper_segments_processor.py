import json
import string
from pod.classes.ai.speech_segment import SpeechSegment
from pod.classes.ai.logging_service import logger


PAUSE_THRESHOLD_SEC = 1
NO_SPEECH_PROB_THRESHOLD = 0.9


def create_speech_segment(
    start_time_sec: int, end_time_sec: int, text: str
) -> SpeechSegment:
    speech_segment = SpeechSegment()
    speech_segment.start_time_sec = start_time_sec
    speech_segment.end_time_sec = end_time_sec
    speech_segment.text = text
    return speech_segment


class WhisperSegmentsProcessor:
    def __init__(self, segments=None, segments_json_path: str = None):
        # one of the parameters should be not None
        if segments is not None:
            self.__segments = segments
        elif segments_json_path is not None:
            self.__segments = self.__load_segments_from_json(segments_json_path)
        else:
            raise Exception("one of the parameters should be not None")

    def __load_segments_from_json(self, segments_json_path: str):
        try:
            with open(segments_json_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(
                f"problem with loading segments from json file: {segments_json_path}\nerror: {e}"
            )
            raise e

    def get_speech_segments(self) -> list:
        start_time = None
        end_time = None
        text = None
        res = []

        for segment in self.__segments["segments"]:
            if segment["no_speech_prob"] > NO_SPEECH_PROB_THRESHOLD:
                if start_time is not None:
                    res.append(create_speech_segment(start_time, end_time, text))
                start_time = None
                end_time = None
                text = None
                continue
            for word in segment["words"]:
                if start_time is None:
                    start_time = word["start"]
                    end_time = word["end"]
                    text = word["word"]
                elif len(text.strip()) == 0 or (
                    text.strip()[-1] in string.punctuation
                    and text.strip()[-1] not in [",", ";"]
                ):
                    res.append(create_speech_segment(start_time, end_time, text))
                    start_time = word["start"]
                    end_time = word["end"]
                    text = word["word"]
                else:
                    end_time = word["end"]
                    text += word["word"]
        if start_time is not None:
            res.append(create_speech_segment(start_time, end_time, text))
        return res
    
