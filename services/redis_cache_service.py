import json
import redis
from typing import Any, Optional, List
from domain.interfaces.cache_interface import ICacheService
from tools.job_store import RedisJobStore

class RedisCacheService(ICacheService):
    def __init__(self, job_store: RedisJobStore):
        self.redis_conn = job_store.get_connection()

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        try:
            val = json.dumps(value)
            if ttl:
                self.redis_conn.setex(key, ttl, val)
            else:
                self.redis_conn.set(key, val)
        except Exception as e:
            print(f"[RedisCacheService] Erro ao setar chave {key}: {e}")

    def get(self, key: str) -> Optional[Any]:
        try:
            val = self.redis_conn.get(key)
            if val:
                return json.loads(val)
            return None
        except Exception as e:
            print(f"[RedisCacheService] Erro ao obter chave {key}: {e}")
            return None

    def delete(self, key: str):
        try:
            self.redis_conn.delete(key)
        except Exception as e:
            print(f"[RedisCacheService] Erro ao deletar chave {key}: {e}")

    def exists(self, key: str) -> bool:
        try:
            return self.redis_conn.exists(key) == 1
        except Exception as e:
            print(f"[RedisCacheService] Erro ao verificar existência da chave {key}: {e}")
            return False

    def get_cached_file_list(self, cache_key: str) -> Optional[List[str]]:
        try:
            val = self.redis_conn.get(cache_key)
            if val:
                return json.loads(val)
            return None
        except Exception as e:
            print(f"[RedisCacheService] Erro ao obter lista de arquivos do cache {cache_key}: {e}")
            return None

    def set_cached_file_list(self, cache_key: str, file_list: List[str], ttl: Optional[int] = 3600):
        try:
            val = json.dumps(file_list)
            self.redis_conn.setex(cache_key, ttl, val)
        except Exception as e:
            print(f"[RedisCacheService] Erro ao salvar lista de arquivos no cache {cache_key}: {e}")
