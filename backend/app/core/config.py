from pydantic_settings import BaseSettings
import logging
import os

logger = logging.getLogger("Settings")

class Settings(BaseSettings):
    # --- Key Vault ---
    KEY_VAULT_URL: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def __init__(self, **values):
        super().__init__(**values)

settings = Settings()
