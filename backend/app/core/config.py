from pydantic_settings import BaseSettings
from typing import Dict, Optional
from backend.app.services.azure_secret_manager import AzureSecretManager, VaultType
import logging
import os

logger = logging.getLogger("Settings")

class Settings(BaseSettings):
    # --- Variáveis Gerais ---
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    
    # --- Azure Resources ---
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_STORAGE_CONTAINER_NAME: str = ""
    
    AZURE_AD_TENANT_ID: str = ""
    AZURE_AD_CLIENT_ID: str = ""
    AZURE_AD_CLIENT_SECRET: str = ""
    
    AZURE_AD_JWKS_URI: Optional[str] = None
    AZURE_AD_ISSUER: Optional[str] = None
    AZURE_AD_AUDIENCE: Optional[str] = None

    # --- MCP CONFIGURATION (A Mágica acontece aqui) ---
    # 1. URL Padrão (Fallback para quando não houver específica)
    MCP_SERVER_BASE_URL: str = "" 
    
    # 2. URLs Específicas (Lidas do Env/Azure)
    # Você cria uma variável para cada "Especialista" futuro
    MCP_URL_EPICOS: Optional[str] = None
    MCP_URL_FEATURES: Optional[str] = None
    MCP_URL_TECH_DEBT: Optional[str] = None

    # 3. O Mapa (Iniciado vazio, populado no __init__)
    MCP_ENDPOINTS: Dict[str, str] = {}

    # --- Redis ---
    REDIS_HOST: Optional[str] = None
    REDIS_PORT: Optional[int] = None
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: Optional[int] = None
    REDIS_SESSION_TTL: int = 86400
    REDIS_USE_SSL: Optional[bool] = None
    REDIS_SSL_CERT_REQS: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Permite variáveis extras no .env sem dar erro

    def __init__(self, **values):
        super().__init__(**values)
        
        # --- Configuração Dinâmica do Azure AD ---
        if not self.AZURE_AD_JWKS_URI and self.AZURE_AD_TENANT_ID:
            self.AZURE_AD_JWKS_URI = f"https://login.microsoftonline.com/{self.AZURE_AD_TENANT_ID}/discovery/v2.0/keys"
        if not self.AZURE_AD_ISSUER and self.AZURE_AD_TENANT_ID:
            self.AZURE_AD_ISSUER = f"https://login.microsoftonline.com/{self.AZURE_AD_TENANT_ID}/v2.0"
        if not self.AZURE_AD_AUDIENCE and self.AZURE_AD_CLIENT_ID:
            self.AZURE_AD_AUDIENCE = self.AZURE_AD_CLIENT_ID

        # --- MONTAGEM DO MAPA DE MCPs ---
        # A lógica é: Tenta pegar a URL específica. Se for None/Vazio, usa a BASE_URL.
        
        self.MCP_ENDPOINTS = {
            # Mapeia o 'analysis_type' -> Variável Específica ou Fallback
            "criacao_epicos_azure_devops": self.MCP_URL_EPICOS or self.MCP_SERVER_BASE_URL,
            "features_generation": self.MCP_URL_FEATURES or self.MCP_SERVER_BASE_URL,
            "tech_debt_analysis": self.MCP_URL_TECH_DEBT or self.MCP_SERVER_BASE_URL,
            # Adicione novos tipos aqui conforme seu projeto cresce
        }
        
        self._log_missing_sensitive_fields()

    def _log_missing_sensitive_fields(self):
        # ... seu código existente ...
        pass
    
    def validate_required_fields(self):
        # ... seu código existente ...
        pass
        
    def get_secret_manager(self, vault_type: str) -> AzureSecretManager:
        # ... seu código existente ...
        return AzureSecretManager(vault_type=VaultType(vault_type))

settings = Settings()
