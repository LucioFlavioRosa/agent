from abc import ABC, abstractmethod
from typing import Any

class IRAGRetriever(ABC):
    @abstractmethod
    def retrieve(self, query: str) -> Any:
        pass