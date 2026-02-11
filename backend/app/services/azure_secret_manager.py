import logging
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

class AzureSecretManager:
    """
    Gerenciador de segredos usando Azure Key Vault, genérico para qualquer cofre cuja URL seja fornecida externamente.
    """
    def __init__(self, key_vault_url: str):
        if not key_vault_url:
            logging.error("URL do Key Vault não fornecida.")
            raise EnvironmentError("A URL do Key Vault deve ser fornecida como parâmetro.")
        self._key_vault_url = key_vault_url
        self._secret_client = None

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
            secret = secret_client.get_secret(secret_name)
            if not secret.value:
                raise ValueError(f"Segredo '{secret_name}' está vazio no Key Vault '{self._key_vault_url}'.")
            return secret.value
        except Exception as e:
            raise ValueError(f"Erro ao obter segredo '{secret_name}' do Azure Key Vault '{self._key_vault_url}': {e}") from e

    def list_secret_names(self):
        secret_client = self._get_secret_client()
        return [prop.name for prop in secret_client.list_properties_of_secrets()]
