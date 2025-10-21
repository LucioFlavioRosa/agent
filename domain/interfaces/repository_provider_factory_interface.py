from abc import ABC, abstractmethod
from typing import Any

class IRepositoryProviderFactory(ABC):
    @abstractmethod
    def get_provider(self, repository_type: str) -> Any:
        pass
