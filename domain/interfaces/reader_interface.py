from abc import ABC, abstractmethod
from typing import Any

class IReader(ABC):
    @abstractmethod
    def read(self, *args, **kwargs) -> Any:
        pass