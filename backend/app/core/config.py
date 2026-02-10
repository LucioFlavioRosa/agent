from pydantic_settings import BaseSettings
from typing import Optional
import logging
import os

logger = logging.getLogger("Settings")

class Settings(BaseSettings):
    # --- MongoDB ---
    MONGODB_URI: str = ""
    MONGODB_DATABASE_NAME: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def __init__(self, **values):
        super().__init__(**values)
        self._validate_mongodb_env()

    def _validate_mongodb_env(self):
        missing = []
        if not self.MONGODB_URI:
            missing.append("MONGODB_URI")
        if not self.MONGODB_DATABASE_NAME:
            missing.append("MONGODB_DATABASE_NAME")
        if missing:
            logger.error(f"[Settings] Variáveis obrigatórias do MongoDB ausentes: {', '.join(missing)}")
            raise ValueError(f"Variáveis obrigatórias do MongoDB ausentes: {', '.join(missing)}")

settings = Settings()
