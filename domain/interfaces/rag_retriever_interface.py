# Arquivo: domain/interfaces/rag_retriever_interface.py

from abc import ABC, abstractmethod

class IRAGRetriever(ABC):
    """
    Interface para sistemas de Retrieval-Augmented Generation (RAG)
    que buscam contexto relevante para uma consulta.
    """
    @abstractmethod
    def buscar_politicas(self, query: str, top_k: int = 5) -> str:
        """
        Busca e retorna um contexto formatado baseado em uma consulta.
        """
        pass
