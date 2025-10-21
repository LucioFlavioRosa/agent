from abc import ABC, abstractmethod
from typing import Any

class ILLMProviderFactory(ABC):
    @abstractmethod
    def create_provider(self, model_name: str, rag_retriever: Any) -> Any:
        pass
