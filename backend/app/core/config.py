from pydantic_settings import BaseSettings
from typing import Optional
import logging

logger = logging.getLogger("Settings")

class Settings(BaseSettings):
    # --- 1. Variáveis de Ambiente Reais (Azure App Service) ---
    KEY_VAULT_URL: str = ""
    REDIS_PERM_TTL: int = 600  # Padrão se não vier do Env

    # --- 2. Placeholders para Segredos do Key Vault ---
   
    # MongoDB
    AZURE_MONGODB_CONNECTION_STRING: Optional[str] = None
    AZURE_MONGODB_DATABASE_NAME: Optional[str] = None

    # Redis
    REDIS_HOST: Optional[str] = None
    REDIS_PORT: Optional[str] = None
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: Optional[str] = None
    REDIS_USE_SSL: Optional[str] = None
    REDIS_SSL_CERT_REQS: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def __init__(self, **values):
        super().__init__(**values)

settings = Settings()
