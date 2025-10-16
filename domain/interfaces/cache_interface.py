from typing import Any, Optional, List

class ICacheService:
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        raise NotImplementedError()

    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError()

    def delete(self, key: str):
        raise NotImplementedError()

    def exists(self, key: str) -> bool:
        raise NotImplementedError()

    def get_cached_file_list(self, cache_key: str) -> Optional[List[str]]:
        raise NotImplementedError()

    def set_cached_file_list(self, cache_key: str, file_list: List[str], ttl: Optional[int] = None):
        raise NotImplementedError()
