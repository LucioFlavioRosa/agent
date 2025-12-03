from pydantic_settings import BaseSettings
from typing import Dict, Optional
from backend.app.services.azure_secret_manager import AzureSecretManager, VaultType
import logging
import os
from backend.app.models.mcp_config_models import MCPConfigRegistry
from backend.app.services.mcp_config_service import MCPConfigService

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
    MCP_SERVER_BASE_URL: str = "" 
    MCP_URL_EPICOS: Optional[str] = None
    MCP_URL_FEATURES: Optional[str] = None
    MCP_URL_TECH_DEBT: Optional[str] = None

    # 3. O Mapa (removido o dicionário hardcoded)
    # MCP_ENDPOINTS: Dict[str, str] = {}

    # --- Redis ---
    REDIS_HOST: Optional[str] = None
    REDIS_PORT: Optional[int] = None
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: Optional[int] = None
    REDIS_SESSION_TTL: int = 86400
    REDIS_USE_SSL: Optional[bool] = None
    REDIS_SSL_CERT_REQS: Optional[str] = None

    # --- MCP Config Registry dinâmico ---
    mcp_config_registry: Optional[MCPConfigRegistry] = None
    
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
        
        # --- Carrega configuração dinâmica de agentes MCP ---
        self.mcp_config_registry = MCPConfigService.load_config()

        self._log_missing_sensitive_fields()
    
    def _log_missing_sensitive_fields(self):
        logger = logging.getLogger("Settings")
        sensitive_fields = [
            "AZURE_STORAGE_CONNECTION_STRING",
            "AZURE_STORAGE_CONTAINER_NAME",
            "AZURE_AD_CLIENT_SECRET",
            "JWT_SECRET_KEY",
            "MCP_SERVER_BASE_URL",
            "REDIS_HOST",
            "REDIS_PORT",
            "REDIS_PASSWORD",
            "REDIS_DB",
            "REDIS_USE_SSL",
            "REDIS_SSL_CERT_REQS"
        ]

        for field in sensitive_fields:
            value = getattr(self, field, None)
            if not value:
                logger.warning(f"[Settings] Campo sensível '{field}' está vazio após inicialização. Ele será preenchido após o carregamento dos segredos.")
            if '_' in field:
                logger.warning(f"[Settings] Atenção: O nome do segredo '{field}' contém underscores. No Azure Key Vault, utilize hífens: '{field.lower().replace('_', '-')}'.")

    def validate_required_fields(self):
        required_fields = [
            "AZURE_STORAGE_CONNECTION_STRING",
            "AZURE_STORAGE_CONTAINER_NAME",
            "AZURE_AD_CLIENT_SECRET",
            "JWT_SECRET_KEY",
            "MCP_SERVER_BASE_URL",
            "REDIS_HOST",
            "REDIS_PORT",
            "REDIS_PASSWORD",
            "REDIS_DB",
            "REDIS_USE_SSL",
            "REDIS_SSL_CERT_REQS"
        ]
        missing = [field for field in required_fields if getattr(self, field, None) in (None, "")]
        if missing:
            raise ValueError(f"Os seguintes campos obrigatórios estão vazios após o carregamento dos segredos: {', '.join(missing)}")
            
    def get_secret_manager(self, vault_type: str) -> AzureSecretManager:
        try:
            vt_enum = VaultType(vault_type)
        except ValueError:
            raise ValueError(f"Tipo de Key Vault inválido: {vault_type}. Esperado: 'azure', 'devops', 'github', 'llm'.")
        return AzureSecretManager(vault_type=vt_enum)

settings = Settings()
