from abc import ABC, abstractmethod
from typing import Any

class IConnection(ABC):
    @abstractmethod
    def connection(self, repositorio: str, repository_type: str, repository_provider: Any) -> Any:
        pass