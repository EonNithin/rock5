def secs_to_hhmmss(secs: int) -> str:
    return str(int(secs / 3600)) + ":" + str(int(secs / 60)) + ":" + f"{secs % 60:.2f}"


class SpeechSegment:
    __start_time_sec: int = None
    __start_time_string: str = None
    __end_time_sec: int = None
    __end_time_string: str = None
    __text: str = None
    __words_count: int = None
    relevance_score: float = None
    relevance_score_gpt: float = None
    cluster_id: int = None
    cluster_relevance_score: float = None
    relevance_score_rag: float = None
    is_relevant: bool = None
    syllabus_classification: str = None

    def __init__(self) -> None:
        pass

    @property
    def start_time_sec(self) -> int:
        return self.__start_time_sec

    @start_time_sec.setter
    def start_time_sec(self, value: int) -> None:
        self.__start_time_sec = value
        self.__start_time_string = secs_to_hhmmss(value)

    @property
    def start_time_string(self) -> str:
        return self.__start_time_string

    @property
    def end_time_sec(self) -> int:
        return self.__end_time_sec

    @end_time_sec.setter
    def end_time_sec(self, value: int) -> None:
        self.__end_time_sec = value
        self.__end_time_string = secs_to_hhmmss(value)

    @property
    def end_time_string(self) -> str:
        return self.__end_time_string

    @property
    def duration_sec(self) -> int:
        return self.__end_time_sec - self.__start_time_sec
    
    @property
    def text(self) -> str:
        return self.__text
    
    @text.setter
    def text(self, value: str) -> None:
        self.__text = value
        self.__words_count = len(self.text.split(" "))

    @property
    def words_count(self) -> int:
        return self.__words_count
