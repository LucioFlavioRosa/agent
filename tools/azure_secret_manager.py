import os
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from domain.interfaces.secret_manager_interface import ISecretManager

class AzureSecretManager(ISecretManager):
    def __init__(self):
        self._key_vault_url = os.environ.get("KEY_VAULT_URL")
        if not self._key_vault_url:
            raise EnvironmentError("A variável de ambiente KEY_VAULT_URL não foi configurada.")
        credential = DefaultAzureCredential()
        self._secret_client = SecretClient(
            vault_url=self._key_vault_url,
            credential=credential
        )

    def get_secret(self, secret_name: str) -> str:
        try:
            secret = self._secret_client.get_secret(secret_name)
            if not secret.value:
                raise ValueError(f"Segredo '{secret_name}' está vazio no Key Vault.")
            return secret.value
        except Exception as e:
            raise ValueError(f"Erro ao obter segredo '{secret_name}' do Azure Key Vault: {e}") from e
