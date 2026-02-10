from pydantic_settings import BaseSettings
from typing import Optional
import logging
import os
from backend.app.services.mcp_config_service import MCPConfigService

logger = logging.getLogger("Settings")

class Settings(BaseSettings):
    # --- Variáveis Gerais ---
    # Removido: JWT_SECRET_KEY, JWT_ALGORITHM, Azure AD, Blob Storage

    # --- MCP CONFIGURATION ---
    MCP_SERVER_BASE_URL: str = "" 
    MCP_URL_EPICOS: Optional[str] = None
    MCP_URL_FEATURES: Optional[str] = None
    MCP_URL_TECH_DEBT: Optional[str] = None

    # --- Redis ---
    REDIS_HOST: Optional[str] = None
    REDIS_PORT: Optional[int] = None
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: Optional[int] = None
    REDIS_SESSION_TTL: int = 86400
    REDIS_USE_SSL: Optional[bool] = None
    REDIS_SSL_CERT_REQS: Optional[str] = None

    # --- MCP Config Registry dinâmico ---
    mcp_config_registry: Optional[object] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def __init__(self, **values):
        super().__init__(**values)
        # Carrega configuração dinâmica de agentes MCP
        self.mcp_config_registry = MCPConfigService.load_config()
        self._log_missing_sensitive_fields()
    
    def _log_missing_sensitive_fields(self):
        logger = logging.getLogger("Settings")
        sensitive_fields = [
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

settings = Settings()
