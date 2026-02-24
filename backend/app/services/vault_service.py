import time
import logging
from typing import Optional, List
from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient
from azure.core.exceptions import ResourceNotFoundError

logger = logging.getLogger("mcp_vault")

class VaultCache:
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

    def set(self, key: str, value: str, ttl: int = 900): # 15 minutos de TTL
        self._cache[key] = (value, time.time() + ttl)


class VaultService:
    def __init__(self, vault_urls: List[str]):
        self.vault_urls = vault_urls
        self.credential = DefaultAzureCredential()
        self.cache = VaultCache()

    async def get_secret(self, base_name: str, company_id: str, group_id: Optional[str] = None) -> Optional[str]:
        """
        Busca um segredo no Key Vault usando fallback entre company_id e group_id.
        - Tenta buscar o segredo com nome: base_name-company_id-group_id (se group_id fornecido)
        - Se não encontrar, tenta base_name-company_id
        - Busca em todos os cofres disponíveis (self.vault_urls)
        - Usa cache para otimizar chamadas
        - Retorna o valor do segredo ou None se não encontrado
        """
        secret_name_full = f"{base_name}-{company_id}-{group_id}" if group_id else f"{base_name}-{company_id}"
        fallback_secret_name = f"{base_name}-{company_id}"
        names_to_try = [secret_name_full]
        if group_id:
            names_to_try.append(fallback_secret_name)

        logger.debug(f"[VaultService] Tentando buscar segredo: {secret_name_full} e fallback: {fallback_secret_name}")

        for secret_name in names_to_try:
            # 1. Tenta no Cache primeiro
            cached_value = self.cache.get(secret_name)
            if cached_value:
                logger.info(f"[VaultService] Segredo '{secret_name}' encontrado no cache.")
                return cached_value

            # 2. Se não está no cache, tenta em todos os cofres
            for url in self.vault_urls:
                logger.debug(f"[VaultService] Tentando buscar segredo '{secret_name}' em '{url}'")
                async with SecretClient(vault_url=url, credential=self.credential) as client:
                    try:
                        secret = await client.get_secret(secret_name)
                        logger.info(f"🔑 [VAULT] Segredo encontrado: {secret_name} em {url}")
                        self.cache.set(secret_name, secret.value)
                        return secret.value
                    except ResourceNotFoundError:
                        logger.debug(f"[VaultService] Segredo '{secret_name}' não encontrado em '{url}'")
                        continue # Não achou neste cofre, tenta o próximo
                    except Exception as e:
                        logger.error(f"❌ [VAULT] Erro ao buscar em {url}: {e}")
                        continue
        
        logger.warning(f"⚠️ [VAULT] Segredo não encontrado em nenhum cofre para {base_name}.")
        return None

    async def get_queue_connection_string(self) -> Optional[str]:
        # Busca no cache primeiro
        cached = self.cache.get("queue-connection-string")
        if cached: return cached

        # Tenta pegar apenas do primeiro cofre (Infra)
        async with SecretClient(vault_url=self.vault_urls[0], credential=self.credential) as client:
            try:
                secret = await client.get_secret("queue-connection-string")
                self.cache.set("queue-connection-string", secret.value, ttl=3600) # Cache de 1 hora
                return secret.value
            except Exception as e:
                logger.error(f"❌ [VAULT] Falha ao buscar connection string da fila: {e}")
                return None
