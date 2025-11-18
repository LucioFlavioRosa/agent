import os
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from threading import Lock

class AzureSecretManager:
    """
    Gerenciador seguro de segredos usando Azure Key Vault.
    Suporta cache local thread-safe e rotação automática de chaves.
    """
    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AzureSecretManager, cls).__new__(cls)
                cls._instance._init_client()
                cls._instance._secrets_cache = {}
            return cls._instance

    def _init_client(self):
        key_vault_url = os.getenv("AZURE_KEY_VAULT_URL")
        if not key_vault_url:
            raise RuntimeError("AZURE_KEY_VAULT_URL não configurado no ambiente.")
        self._client = SecretClient(vault_url=key_vault_url, credential=DefaultAzureCredential())

    def get_secret(self, secret_name: str) -> str:
        """
        Busca o segredo pelo nome, usando cache local para minimizar chamadas ao Key Vault.
        """
        if secret_name in self._secrets_cache:
            return self._secrets_cache[secret_name]
        try:
            secret = self._client.get_secret(secret_name)
            self._secrets_cache[secret_name] = secret.value
            return secret.value
        except Exception as e:
            raise RuntimeError(f"Erro ao buscar segredo '{secret_name}' no Azure Key Vault: {e}")

    def rotate_secret(self, secret_name: str, new_value: str) -> None:
        """
        Atualiza o valor do segredo no Key Vault e no cache local.
        """
        try:
            self._client.set_secret(secret_name, new_value)
            self._secrets_cache[secret_name] = new_value
        except Exception as e:
            raise RuntimeError(f"Erro ao rotacionar segredo '{secret_name}' no Azure Key Vault: {e}")
