import os
from enum import Enum
from typing import Optional
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from tools.user_email_parser import UserEmailParser

class VaultType(Enum):
    AZURE_INFRASTRUCTURE = 'azure_infrastructure'  # kv-codeai-azure-dev-usc
    LLM = 'llm'                                    # kv-codeai-llm-dev-usc
    GITHUB = 'github'                              # kv-codeai-github-dev-usc
    AZURE_DEVOPS = 'azure_devops'                  # kv-codeai-devops-dev-usc

class AzureSecretManager:
    _VAULT_URLS = {
        VaultType.AZURE_INFRASTRUCTURE: os.getenv('AZURE_KEY_VAULT_AZURE_INFRASTRUCTURE_URL'),  # kv-codeai-azure-dev-usc
        VaultType.LLM: os.getenv('AZURE_KEY_VAULT_LLM_URL'),                                    # kv-codeai-llm-dev-usc
        VaultType.GITHUB: os.getenv('AZURE_KEY_VAULT_GITHUB_URL'),                              # kv-codeai-github-dev-usc
        VaultType.AZURE_DEVOPS: os.getenv('AZURE_KEY_VAULT_AZURE_DEVOPS_URL'),                  # kv-codeai-devops-dev-usc
    }

    def __init__(self, vault_type: VaultType = VaultType.AZURE_INFRASTRUCTURE):
        self.vault_type = vault_type
        self.vault_url = self._get_vault_url(vault_type)
        if not self.vault_url:
            raise RuntimeError(f"Azure Key Vault URL não definida para o tipo '{vault_type.value}'.")
        self.credential = DefaultAzureCredential()
        self.client = SecretClient(vault_url=self.vault_url, credential=self.credential)

    def _get_vault_url(self, vault_type: VaultType) -> Optional[str]:
        return self._VAULT_URLS.get(vault_type)

    def get_secret(self, secret_name: str) -> str:
        try:
            secret = self.client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            print(f"[AzureSecretManager] Erro ao buscar secret '{secret_name}' no vault '{self.vault_url}': {e}")
            raise ValueError(f"Secret '{secret_name}' não encontrado ou erro de acesso ao Key Vault.")

    def get_secret_with_user_context(self, secret_base_name: str, user_email: str, group_resolver: Optional[object] = None) -> str:
        """
        Obtém o secret usando o email completo do usuário e o group_resolver.
        O nome do secret é construído como '{secret_base_name}-{grupo}-{empresa}',
        onde grupo é obtido via group_resolver.get_group_for_user(user_email) e empresa via UserEmailParser.parse_email(user_email).
        """
        if group_resolver is not None:
            grupo = group_resolver.get_group_for_user(user_email)
            _, empresa = UserEmailParser.parse_email(user_email)
            secret_name = f"{secret_base_name}-{grupo}-{empresa}"
        else:
            # Fallback: utiliza apenas usuario e empresa (não recomendado)
            usuario, empresa = UserEmailParser.parse_email(user_email)
            secret_name = f"{secret_base_name}-{usuario}-{empresa}"
        try:
            secret = self.client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            print(f"[AzureSecretManager] Erro ao buscar secret '{secret_name}' no vault '{self.vault_url}': {e}")
            raise ValueError(f"Secret '{secret_name}' não encontrado ou erro de acesso ao Key Vault.")
