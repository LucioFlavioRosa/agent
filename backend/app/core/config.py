from pydantic_settings import BaseSettings
from typing import Dict, Optional
from backend.app.services.azure_secret_manager import AzureSecretManager, VaultType

class Settings(BaseSettings):
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_STORAGE_CONTAINER_NAME: str = ""
    MCP_SERVER_BASE_URL: str = "http://mcp-app-service.azurewebsites.net"

    # Novos campos para Azure AD (moderno, sem ROPC)
    AZURE_AD_TENANT_ID: str = ""
    AZURE_AD_CLIENT_ID: str = ""
    AZURE_AD_CLIENT_SECRET: str = ""
    
    # Novos campos para validação JWT segura
    AZURE_AD_JWKS_URI: Optional[str] = None  # Ex: https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys
    AZURE_AD_ISSUER: Optional[str] = None    # Ex: https://login.microsoftonline.com/{tenant_id}/v2.0
    AZURE_AD_AUDIENCE: Optional[str] = None  # Geralmente o client_id da API registrada no Azure AD

    def load_secrets_from_keyvault(self):
        """
        Método explícito para buscar segredos e atualizar o settings.
        Deve ser chamado no startup do app.
        """
        try:
            # Instancia o gerenciador (ajuste o vault_type conforme sua lógica)
            secret_manager = self.get_secret_manager(vault_type="azure") 
            
            # Busca o segredo. O nome "azure-storage-connection-string" deve ser o nome exato NO KEY VAULT
            # O Key Vault geralmente usa hífens, o Python usa underscores.
            conn_string = secret_manager.get_secret("azure-storage-connection-string")
            
            if conn_string:
                self.AZURE_STORAGE_CONNECTION_STRING = conn_string
                print("Segredos carregados do Key Vault com sucesso.")
            else:
                print("AVISO: Connection String não encontrada no Key Vault.")
                
        except Exception as e:
            print(f"Erro crítico ao carregar segredos do Key Vault: {e}")

    # Mapeamento de analysis_type para endpoints MCP
    MCP_ENDPOINTS: Dict[str, str] = {
        "criacao_epicos_azure_devops": "https://mcp-epicos.azurewebsites.net"
        # Adicione outros mapeamentos conforme necessário
    }
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def __init__(self, **values):
        super().__init__(**values)
        # Preenche automaticamente os campos JWKS/ISSUER/AUDIENCE se não definidos
        if not self.AZURE_AD_JWKS_URI and self.AZURE_AD_TENANT_ID:
            self.AZURE_AD_JWKS_URI = f"https://login.microsoftonline.com/{self.AZURE_AD_TENANT_ID}/discovery/v2.0/keys"
        if not self.AZURE_AD_ISSUER and self.AZURE_AD_TENANT_ID:
            self.AZURE_AD_ISSUER = f"https://login.microsoftonline.com/{self.AZURE_AD_TENANT_ID}/v2.0"
        if not self.AZURE_AD_AUDIENCE and self.AZURE_AD_CLIENT_ID:
            self.AZURE_AD_AUDIENCE = self.AZURE_AD_CLIENT_ID

    def get_secret_manager(self, vault_type: str) -> AzureSecretManager:
        """
        Retorna uma instância do AzureSecretManager configurada para o cofre correto.
        Args:
            vault_type: Tipo do cofre ('azure', 'devops', 'github', 'llm')
        Returns:
            AzureSecretManager: Instância pronta para uso
        Raises:
            ValueError: Se o tipo for inválido
        """
        try:
            vt_enum = VaultType(vault_type)
        except ValueError:
            raise ValueError(f"Tipo de Key Vault inválido: {vault_type}. Esperado: 'azure', 'devops', 'github', 'llm'.")
        return AzureSecretManager(vault_type=vt_enum)

settings = Settings()
