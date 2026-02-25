import time
import logging
import re
from typing import Optional, List
from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient
from azure.core.exceptions import ResourceNotFoundError

logger = logging.getLogger("mcp_vault")

class VaultCache:
    """
    Cache simples com TTL para segredos de cofres.
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

class VaultService:
    def __init__(self, vault_urls: List[str]):
        self.vault_urls = vault_urls
        self.credential = DefaultAzureCredential()
        self.cache = VaultCache()

    def _sanitize_name(self, name: str) -> str:
        """
        Garante que o nome do segredo siga a regra do Azure Key Vault:
        Apenas caracteres alfanuméricos e hífens (^[0-9a-zA-Z-]+$).
        """
        if not name:
            return name
        sanitized = re.sub(r'[^0-9a-zA-Z-]+', '-', name)
        return sanitized.strip('-')

    async def get_secret(self, base_name: str, company_id: str, group_id: Optional[str] = None) -> Optional[str]:
        safe_company_id = self._sanitize_name(company_id)
        safe_group_id = self._sanitize_name(group_id) if group_id else None
        secret_name_full = f"{base_name}-{safe_company_id}-{safe_group_id}" if safe_group_id else f"{base_name}-{safe_company_id}"
        fallback_secret_name = f"{base_name}-{safe_company_id}"
        names_to_try = [secret_name_full]
        if safe_group_id:
            names_to_try.append(fallback_secret_name)
        logger.info(f"vault_secret_busca_iniciada | base_name={base_name} | company_id={company_id} | group_id={group_id}")
        for secret_name in names_to_try:
            cached_value = self.cache.get(secret_name)
            if cached_value:
                logger.info(f"vault_secret_encontrado | secret_name={secret_name} | origem=cache")
                return cached_value
            for url in self.vault_urls:
                try:
                    async with SecretClient(vault_url=url, credential=self.credential) as client:
                        secret = await client.get_secret(secret_name)
                        self.cache.set(secret_name, secret.value)
                        logger.info(f"vault_secret_encontrado | secret_name={secret_name} | vault_url={url}")
                        return secret.value
                except ResourceNotFoundError:
                    continue
                except Exception as e:
                    logger.error(f"vault_secret_erro_acesso | secret_name={secret_name} | vault_url={url} | erro={str(e)}")
                    continue
        logger.info(f"vault_secret_nao_encontrado | base_name={base_name} | company_id={company_id} | group_id={group_id}")
        return None

    async def get_queue_connection_string(self) -> Optional[str]:
        cached = self.cache.get("queue-connection-string")
        if cached:
            logger.info("vault_secret_encontrado | secret_name=queue-connection-string | origem=cache")
            return cached
        logger.info("vault_secret_busca_iniciada | base_name=queue-connection-string")
        async with SecretClient(vault_url=self.vault_urls[0], credential=self.credential) as client:
            try:
                secret = await client.get_secret("queue-connection-string")
                self.cache.set("queue-connection-string", secret.value, ttl=3600)
                logger.info(f"vault_secret_encontrado | secret_name=queue-connection-string | vault_url={self.vault_urls[0]}")
                return secret.value
            except Exception:
                logger.info("vault_secret_nao_encontrado | base_name=queue-connection-string")
                return None
