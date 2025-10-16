from abc import ABC, abstractmethod
from typing import Any, Optional, List

class ICacheService(ABC):
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def delete(self, key: str):
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        pass

    @abstractmethod
    def get_cached_file_list(self, cache_key: str) -> Optional[List[str]]:
        pass

    @abstractmethod
    def set_cached_file_list(self, cache_key: str, file_list: List[str], ttl: Optional[int] = 3600):
        pass
