import asyncio
from typing import Optional
from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient

class SecretNotFoundException(Exception):
    def __init__(self, secret_name: str, company_id: str, group_id: Optional[str] = None):
        self.secret_name = secret_name
        self.company_id = company_id
        self.group_id = group_id
        super().__init__(f"Segredo '{secret_name}' não encontrado para company_id='{company_id}' group_id='{group_id}'")

class SecretsManager:
    def __init__(self, azure_cofre_urls: dict):
        """
        azure_cofre_urls: dict
            {
                "infra": "https://cofre-infra.vault.azure.net/",
                "llm": "https://cofre-llm.vault.azure.net/",
                "organizadores": "https://cofre-organizadores.vault.azure.net/"
            }
        """
        self.azure_cofre_urls = azure_cofre_urls
        self._clients = {}
        self._cache = {}
        self._credential = DefaultAzureCredential()

    async def _get_client(self, cofre_tipo: str) -> SecretClient:
        if cofre_tipo not in self._clients:
            vault_url = self.azure_cofre_urls.get(cofre_tipo)
            if not vault_url:
                raise ValueError(f"URL do cofre '{cofre_tipo}' não configurada.")
            self._clients[cofre_tipo] = SecretClient(vault_url=vault_url, credential=self._credential)
        return self._clients[cofre_tipo]

    async def _get_secret(self, cofre_tipo: str, secret_name: str, company_id: str, group_id: Optional[str] = None) -> str:
        cache_key = f"{cofre_tipo}:{secret_name}:{company_id}:{group_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        client = await self._get_client(cofre_tipo)
        # Fallback: tenta com group_id, depois sem
        tried_keys = []
        if group_id:
            secret_full_name = f"{secret_name}-{company_id}-{group_id}"
            tried_keys.append(secret_full_name)
            try:
                secret = await client.get_secret(secret_full_name)
                self._cache[cache_key] = secret.value
                return secret.value
            except Exception:
                pass
        secret_full_name = f"{secret_name}-{company_id}"
        tried_keys.append(secret_full_name)
        try:
            secret = await client.get_secret(secret_full_name)
            self._cache[cache_key] = secret.value
            return secret.value
        except Exception:
            pass
        raise SecretNotFoundException(secret_name, company_id, group_id)

    async def get_blob_storage_connection_string(self, company_id: str, group_id: Optional[str] = None) -> str:
        return await self._get_secret(
            cofre_tipo="infra",
            secret_name="blobstorage-conection-string",
            company_id=company_id,
            group_id=group_id
        )

    async def get_blob_storage_container_name(self, company_id: str, group_id: Optional[str] = None) -> str:
        return await self._get_secret(
            cofre_tipo="infra",
            secret_name="blobstorage-contanier-name",
            company_id=company_id,
            group_id=group_id
        )

    async def get_openai_api_key(self, company_id: str, group_id: Optional[str] = None) -> str:
        return await self._get_secret(
            cofre_tipo="llm",
            secret_name="openai-api-key",
            company_id=company_id,
            group_id=group_id
        )

    async def get_project_organizer_secret(self, secret_name: str, company_id: str, group_id: Optional[str] = None) -> str:
        return await self._get_secret(
            cofre_tipo="organizadores",
            secret_name=secret_name,
            company_id=company_id,
            group_id=group_id
        )
