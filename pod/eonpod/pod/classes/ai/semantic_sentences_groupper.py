from semantic_split import (
    SimilarSentenceSplitter,
    SentenceTransformersSimilarity,
    SpacySentenceSplitter,
)


class SemanticSentencesGroupper:
    __model = SentenceTransformersSimilarity()
    __sentence_splitter = SpacySentenceSplitter()
    __splitter = SimilarSentenceSplitter(__model, __sentence_splitter)

    def __init__(self, text: str) -> None:
        self.__text = text

    def group(self) -> list:
        res = self.__splitter.split(self.__text)
        return res
    