import asyncio
from typing import Optional, Dict
from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient
from azure.core.exceptions import ResourceNotFoundError

# Exceção customizada para segredo não encontrado
class VaultSecretNotFoundError(Exception):
    def __init__(self, secret_name: str, vault_url: str):
        super().__init__(f"Secret '{secret_name}' not found in vault '{vault_url}'.")

# Cache simples de segredos (thread-safe para asyncio)
class VaultCache:
    def __init__(self):
        self._cache: Dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            return self._cache.get(key)

    async def set(self, key: str, value: str):
        async with self._lock:
            self._cache[key] = value

# Settings de URLs dos cofres e conexão fixa da fila
class Settings:
    # URLs dos cofres (devem ser configuradas no ambiente)
    VAULT_INFRASTRUCTURE_URL = "https://infra-vault-url.vault.azure.net/"
    VAULT_LLM_URL = "https://llm-vault-url.vault.azure.net/"
    VAULT_INTEGRATIONS_URL = "https://integrations-vault-url.vault.azure.net/"
    # Conexão fixa para fila
    AZURE_STORAGE_QUEUE_CONNECTION_STRING = "sua_connection_string_da_fila"

class VaultService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._credential = DefaultAzureCredential()
        self._cache = VaultCache()

    def _get_vault_url(self, vault_type: str) -> str:
        if vault_type == "infrastructure":
            return self.settings.VAULT_INFRASTRUCTURE_URL
        elif vault_type == "llm":
            return self.settings.VAULT_LLM_URL
        elif vault_type == "integrations":
            return self.settings.VAULT_INTEGRATIONS_URL
        else:
            raise ValueError(f"Vault type '{vault_type}' is not supported.")

    async def get_secret(
        self,
        key_base_name: str,
        company_id: str,
        group_id: Optional[str],
        vault_type: str
    ) -> str:
        vault_url = self._get_vault_url(vault_type)
        # Nome da chave com group_id
        if group_id:
            secret_name = f"{key_base_name}-{company_id}-{group_id}"
        else:
            secret_name = f"{key_base_name}-{company_id}"

        # Fallback: nome da chave sem group_id
        fallback_secret_name = f"{key_base_name}-{company_id}"

        # Busca no cache
        cached_value = await self._cache.get(f"{vault_url}:{secret_name}")
        if cached_value is not None:
            return cached_value

        if group_id:
            # Busca com group_id
            try:
                client = SecretClient(vault_url=vault_url, credential=self._credential)
                secret = await client.get_secret(secret_name)
                await self._cache.set(f"{vault_url}:{secret_name}", secret.value)
                return secret.value
            except ResourceNotFoundError:
                pass
            finally:
                await client.close()

        # Busca fallback sem group_id
        try:
            client = SecretClient(vault_url=vault_url, credential=self._credential)
            secret = await client.get_secret(fallback_secret_name)
            await self._cache.set(f"{vault_url}:{fallback_secret_name}", secret.value)
            return secret.value
        except ResourceNotFoundError:
            raise VaultSecretNotFoundError(fallback_secret_name, vault_url)
        finally:
            await client.close()

    def get_queue_connection_string(self) -> str:
        return self.settings.AZURE_STORAGE_QUEUE_CONNECTION_STRING
