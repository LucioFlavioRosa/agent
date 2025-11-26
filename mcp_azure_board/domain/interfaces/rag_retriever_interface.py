from abc import ABC, abstractmethod
from typing import Any

class IRAGRetriever(ABC):
    @abstractmethod
    def buscar_politicas(self, query: str) -> Any:
        pass
