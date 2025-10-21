import os
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from domain.interfaces.secret_manager_interface import ISecretManager

class AzureSecretManager(ISecretManager):
    """
    Implementação do gerenciador de segredos usando Azure Key Vault.
    Responsabilidade única: gerenciar segredos do Azure Key Vault.
    """
    def __init__(self):
        self._secret_client = None
        self._key_vault_url = os.environ.get("KEY_VAULT_URL")
        if not self._key_vault_url:
            raise EnvironmentError("A variável de ambiente KEY_VAULT_URL não foi configurada.")
    
    def _get_secret_client(self) -> SecretClient:
        """Lazy initialization do cliente de segredos."""
        if self._secret_client is None:
            print("Conectando ao Azure Key Vault...")
            credential = DefaultAzureCredential()
            self._secret_client = SecretClient(
                vault_url=self._key_vault_url, 
                credential=credential
            )
        return self._secret_client
    
    def get_secret(self, secret_name: str) -> str:
        """
        Obtém um segredo do Azure Key Vault.
        
        Args:
            secret_name: Nome do segredo no Key Vault
            
        Returns:
            str: Valor do segredo
            
        Raises:
            ValueError: Se o segredo não for encontrado
        """
        try:
            secret_client = self._get_secret_client()
            secret = secret_client.get_secret(secret_name)
            if not secret.value:
                raise ValueError(f"Segredo '{secret_name}' está vazio no Key Vault.")
            return secret.value
        except Exception as e:
            raise ValueError(f"Erro ao obter segredo '{secret_name}' do Azure Key Vault: {e}") from e
