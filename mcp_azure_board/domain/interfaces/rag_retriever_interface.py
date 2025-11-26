from abc import ABC, abstractmethod

class IRAGRetriever(ABC):
    @abstractmethod
    def retrieve(self, query: str, context: dict = None) -> str:
        """
        Recupera informações relevantes usando RAG (Retrieval-Augmented Generation).
        :param query: Consulta de busca.
        :param context: Contexto adicional para a busca.
        :return: Texto relevante recuperado.
        """
        pass
