from FlagEmbedding import BGEM3FlagModel


class SimilarityEstimator:
    __similarity_model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)

    def __init__(self, text: str) -> None:
        self.__text = text
        self.__general_embedding = SimilarityEstimator.__similarity_model.encode(
            text, batch_size=12, max_length=8192
        )["dense_vecs"]
        pass

    def calculate_similarity(self, text: str) -> float:
        text_embedding = self.__similarity_model.encode(
            text, batch_size=12, max_length=8192
        )["dense_vecs"]

        similarity = text_embedding @ self.__general_embedding.T
        return similarity
