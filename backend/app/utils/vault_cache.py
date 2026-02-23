import time
from typing import Optional

class VaultCache:
    """
    Cache simples com TTL para segredos de cofres.
    Chave: f"{vault_type}:{key_name}"
    TTL padrão: 900 segundos (15 minutos)
    """
    def __init__(self):
        self._cache = {}

    def get(self, key: str) -> Optional[str]:
        entry = self._cache.get(key)
        if not entry:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del self._cache[key]
            return None
        return value

    def set(self, key: str, value: str, ttl: int = 900):
        expires_at = time.time() + ttl
        self._cache[key] = (value, expires_at)
