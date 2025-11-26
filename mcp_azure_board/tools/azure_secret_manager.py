import os
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

class AzureSecretManager:
    def __init__(self):
        self.vault_url = os.getenv('AZURE_KEY_VAULT_URL')
        if not self.vault_url:
            raise RuntimeError('AZURE_KEY_VAULT_URL não definido.')
        self.credential = DefaultAzureCredential()
        self.client = SecretClient(vault_url=self.vault_url, credential=self.credential)

    def get_secret(self, secret_name: str) -> str:
        try:
            secret = self.client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            print(f"[AzureSecretManager] Erro ao buscar secret '{secret_name}': {e}")
            raise
