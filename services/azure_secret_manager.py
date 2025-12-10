import os
import logging
from enum import Enum
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def _validate_env_var(var_name, var_value):
    if not var_value:
        return False, f"[Settings] Campo sensível '{var_name}' está vazio após inicialização. Ele será preenchido após o carregamento dos segredos."
    if '_' in var_name:
        return True, f"[Settings] Atenção: O nome do segredo '{var_name}' contém underscores. No Azure Key Vault, utilize hífens: '{var_name.lower().replace('_', '-')}'."
    return True, None

class VaultType(str, Enum):
    AZURE = 'azure'
    DEVOPS = 'devops'
    GITHUB = 'github'
    LLM = 'llm'

class AzureSecretManager:
    def __init__(self, vault_type: VaultType):
        self._secret_client = None
        self.vault_type = vault_type
        self._vault_urls = {
            VaultType.AZURE: os.environ.get('AZURE_KV_URL'),
            VaultType.DEVOPS: os.environ.get('DEVOPS_KV_URL'),
            VaultType.GITHUB: os.environ.get('GITHUB_KV_URL'),
            VaultType.LLM: os.environ.get('LLM_KV_URL')
        }
        self._key_vault_url = self._vault_urls.get(self.vault_type)
        if not self._key_vault_url:
            logging.error(f"URL do Key Vault para '{self.vault_type}' não encontrada nas variáveis de ambiente.")
            raise EnvironmentError(f"A URL do Key Vault para o tipo '{self.vault_type}' não foi configurada na variável de ambiente.")
        if not self._key_vault_url.startswith("https://"):
            raise EnvironmentError(f"A URL do Key Vault para o tipo '{self.vault_type}' é inválida: {self._key_vault_url}")

    def _get_secret_client(self) -> SecretClient:
        if self._secret_client is None:
            credential = DefaultAzureCredential()
            self._secret_client = SecretClient(
                vault_url=self._key_vault_url,
                credential=credential
            )
        return self._secret_client

    def get_secret(self, secret_name: str) -> str:
        logger = logging.getLogger("AzureSecretManager")
        if '_' in secret_name:
            logger.warning(f"[AzureSecretManager] O nome do segredo '{secret_name}' contém underscores. O Azure Key Vault prefere hífens. Tente: '{secret_name.lower().replace('_', '-')}'")
        try:
            secret_client = self._get_secret_client()
            logger.info(f"Buscando segredo '{secret_name}' no cofre '{self._key_vault_url}' (tipo: {self.vault_type})")
            secret = secret_client.get_secret(secret_name)
            if not secret.value:
                raise ValueError(f"Segredo '{secret_name}' está vazio no Key Vault '{self._key_vault_url}'.")
            return secret.value
        except Exception as e:
            logger.error(f"Erro ao obter segredo '{secret_name}' do Azure Key Vault '{self._key_vault_url}': {e}")
            raise ValueError(f"Erro ao obter segredo '{secret_name}' do Azure Key Vault '{self._key_vault_url}'.")
