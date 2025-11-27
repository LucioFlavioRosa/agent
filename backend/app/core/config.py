from pydantic_settings import BaseSettings
from typing import Dict

class Settings(BaseSettings):
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    AZURE_STORAGE_CONNECTION_STRING: str
    AZURE_STORAGE_CONTAINER_NAME: str
    MCP_SERVER_BASE_URL: str = "http://mcp-app-service.azurewebsites.net"

    # Novos campos para Azure AD (moderno, sem ROPC)
    AZURE_AD_TENANT_ID: str
    AZURE_AD_CLIENT_ID: str
    AZURE_AD_CLIENT_SECRET: str
    
    # Novos campos para validação JWT segura
    AZURE_AD_JWKS_URI: str = None  # Ex: https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys
    AZURE_AD_ISSUER: str = None    # Ex: https://login.microsoftonline.com/{tenant_id}/v2.0
    AZURE_AD_AUDIENCE: str = None  # Geralmente o client_id da API registrada no Azure AD

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

settings = Settings()
