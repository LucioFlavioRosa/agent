import os
from enum import Enum
from typing import Optional
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

class VaultType(Enum):
    LLM = 'llm'
    REPOSITORY = 'repository'
    DEFAULT = 'default'
    BLOB_STORAGE = 'blob_storage'

class AzureSecretManager:
    _VAULT_URLS = {
        VaultType.LLM: os.getenv('AZURE_KEY_VAULT_LLM_URL'),
        VaultType.REPOSITORY: os.getenv('AZURE_KEY_VAULT_REPOSITORY_URL'),
        VaultType.DEFAULT: os.getenv('AZURE_KEY_VAULT_URL'),
        VaultType.BLOB_STORAGE: os.getenv('AZURE_KEY_VAULT_BLOB_STORAGE_URL')
    }

    def __init__(self, vault_type: VaultType = VaultType.DEFAULT):
        self.vault_type = vault_type
        self.vault_url = self._get_vault_url(vault_type)
        if not self.vault_url:
            raise RuntimeError(f"Azure Key Vault URL não definida para o tipo '{vault_type.value}'.")
        self.credential = DefaultAzureCredential()
        self.client = SecretClient(vault_url=self.vault_url, credential=self.credential)

    def _get_vault_url(self, vault_type: VaultType) -> Optional[str]:
        url = self._VAULT_URLS.get(vault_type)
        if url:
            return url
        # fallback para DEFAULT se não encontrar
        return self._VAULT_URLS.get(VaultType.DEFAULT)

    def get_secret(self, secret_name: str) -> str:
        # Suporte para secrets AWS
        try:
            secret = self.client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            print(f"[AzureSecretManager] Erro ao buscar secret '{secret_name}' no vault '{self.vault_url}': {e}")
            raise ValueError(f"Secret '{secret_name}' não encontrado ou erro de acesso ao Key Vault.")
