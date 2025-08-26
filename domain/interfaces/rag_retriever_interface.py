# Arquivo: domain/interfaces/rag_retriever_interface.py
from abc import ABC, abstractmethod

class IRAGRetriever(ABC):
    """
    Interface para sistemas de Retrieval-Augmented Generation (RAG)
    Implementação obrigatória: AzureAISearchRAGRetriever em tools/rag_retriever.py.
    """
    @abstractmethod
    def buscar_politicas(self, query: str, top_k: int = 5) -> str:
        """
        Busca e retorna um contexto formatado baseado em uma consulta.
        """
        pass
