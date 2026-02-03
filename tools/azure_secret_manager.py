import os
from enum import Enum
from typing import Optional
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from tools.user_email_parser import UserEmailParser

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
        return self._VAULT_URLS.get(VaultType.DEFAULT)

    def get_secret(self, secret_name: str) -> str:
        try:
            secret = self.client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            print(f"[AzureSecretManager] Erro ao buscar secret '{secret_name}' no vault '{self.vault_url}': {e}")
            raise ValueError(f"Secret '{secret_name}' não encontrado ou erro de acesso ao Key Vault.")

    def get_secret_with_user_context(self, secret_base_name: str, user_email: str) -> str:
        """
        Busca o secret usando o padrão '{secret_base_name}-{usuario}-{empresa}'
        Não há fallback: se não existir, lança erro.
        """
        usuario, empresa = UserEmailParser.parse_email(user_email)
        secret_name = f"{secret_base_name}-{usuario}-{empresa}"
        try:
            secret = self.client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            print(f"[AzureSecretManager] Erro ao buscar secret '{secret_name}' no vault '{self.vault_url}': {e}")
            raise ValueError(f"Secret '{secret_name}' não encontrado ou erro de acesso ao Key Vault.")
