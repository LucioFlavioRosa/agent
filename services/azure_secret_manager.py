import os
import logging
from enum import Enum
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

class VaultType(str, Enum):
    AZURE = 'azure'
    DEVOPS = 'devops'
    GITHUB = 'github'
    LLM = 'llm'

class AzureSecretManager:
    """
    Gerenciador de segredos usando Azure Key Vault, suportando múltiplos cofres por objetivo.
    """
    def __init__(self, vault_type: VaultType):
        self._secret_client = None
        self.vault_type = vault_type
        
        # O gerenciador busca as variáveis de ambiente diretamente via OS,
        # o que é perfeito para evitar dependência circular com o config.py
        self._vault_urls = {
            VaultType.AZURE: os.environ.get('AZURE_KV_URL'),
            VaultType.DEVOPS: os.environ.get('DEVOPS_KV_URL'),
            VaultType.GITHUB: os.environ.get('GITHUB_KV_URL'),
            VaultType.LLM: os.environ.get('LLM_KV_URL')
        }
        
        self._key_vault_url = self._vault_urls.get(self.vault_type)
        
        if not self._key_vault_url:
            # Dica: Adicionei log aqui para ajudar no debug do deploy
            logging.error(f"URL do Key Vault para '{self.vault_type}' não encontrada nas variáveis de ambiente.")
            raise EnvironmentError(f"A URL do Key Vault para o tipo '{self.vault_type}' não foi configurada na variável de ambiente.")

    def _get_secret_client(self) -> SecretClient:
        """Inicialização lazy do cliente de segredos para o cofre correto."""
        if self._secret_client is None:
            credential = DefaultAzureCredential()
            self._secret_client = SecretClient(
                vault_url=self._key_vault_url,
                credential=credential
            )
        return self._secret_client

    def get_secret(self, secret_name: str) -> str:
        """
        Obtém um segredo do Azure Key Vault do cofre configurado para o tipo.
        """
        logger = logging.getLogger("AzureSecretManager")
        
        # Validação: loga aviso se o nome do segredo contiver underscores
        if '_' in secret_name:
            logger.warning(f"[AzureSecretManager] O nome do segredo '{secret_name}' contém underscores. O Azure Key Vault prefere hífens. Tente: '{secret_name.lower().replace('_', '-')}'")
        
        try:
            secret_client = self._get_secret_client()
            secret = secret_client.get_secret(secret_name)
            if not secret.value:
                raise ValueError(f"Segredo '{secret_name}' está vazio no Key Vault '{self._key_vault_url}'.")
            return secret.value
        except Exception as e:
            raise ValueError(f"Erro ao obter segredo '{secret_name}' do Azure Key Vault '{self._key_vault_url}': {e}") from e
