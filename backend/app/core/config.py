from pydantic_settings import BaseSettings
import logging
import os

logger = logging.getLogger("Settings")

class Settings(BaseSettings):
    # --- Key Vault ---
    KEY_VAULT_URL: str = ""
    # --- MongoDB ---
    MONGODB_URI: str = ""
    MONGODB_DATABASE_NAME: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def __init__(self, **values):
        super().__init__(**values)
        # Removida validação de MONGODB_URI e MONGODB_DATABASE_NAME do construtor;
        # a validação de campos obrigatórios deve ocorrer após carregamento dos segredos.

settings = Settings()
