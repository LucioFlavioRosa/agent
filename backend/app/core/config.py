from pydantic_settings import BaseSettings
from typing import Dict

class Settings(BaseSettings):
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    AZURE_STORAGE_CONNECTION_STRING: str
    AZURE_STORAGE_CONTAINER_NAME: str
    MCP_SERVER_BASE_URL: str = "http://mcp-app-service.azurewebsites.net"
    
    # Novos campos para Azure AD
    AZURE_AD_TENANT_ID: str
    AZURE_AD_CLIENT_ID: str
    AZURE_AD_CLIENT_SECRET: str
    
    # Mapeamento de analysis_type para endpoints MCP
    MCP_ENDPOINTS: Dict[str, str] = {
        "criacao_epicos_azure_devops": "https://mcp-epicos.azurewebsites.net"
        # Adicione outros mapeamentos conforme necessário
    }
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
