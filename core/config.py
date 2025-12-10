import os
import logging
from typing import Optional
from pydantic_settings import BaseSettings
from services.azure_secret_manager import AzureSecretManager, VaultType, _validate_env_var

logger = logging.getLogger("Settings")

class Settings(BaseSettings):
    REDIS_HOST: Optional[str] = None
    REDIS_PORT: Optional[int] = None
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: Optional[int] = None
    REDIS_SESSION_TTL: int = 86400
    REDIS_USE_SSL: Optional[bool] = None
    REDIS_SSL_CERT_REQS: Optional[str] = None

    AZURE_KV_URL: Optional[str] = None
    DEVOPS_KV_URL: Optional[str] = None
    GITHUB_KV_URL: Optional[str] = None
    LLM_KV_URL: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def __init__(self, **values):
        super().__init__(**values)
        self._load_env_vars()
        self.validate_vault_configuration()

    def _load_env_vars(self):
        self.AZURE_KV_URL = os.environ.get("AZURE_KV_URL", self.AZURE_KV_URL)
        self.DEVOPS_KV_URL = os.environ.get("DEVOPS_KV_URL", self.DEVOPS_KV_URL)
        self.GITHUB_KV_URL = os.environ.get("GITHUB_KV_URL", self.GITHUB_KV_URL)
        self.LLM_KV_URL = os.environ.get("LLM_KV_URL", self.LLM_KV_URL)
        self.REDIS_HOST = os.environ.get("REDIS_HOST", self.REDIS_HOST)
        self.REDIS_PORT = int(os.environ.get("REDIS_PORT", self.REDIS_PORT or 6379))
        self.REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", self.REDIS_PASSWORD)
        self.REDIS_DB = int(os.environ.get("REDIS_DB", self.REDIS_DB or 0))
        self.REDIS_SESSION_TTL = int(os.environ.get("REDIS_SESSION_TTL", self.REDIS_SESSION_TTL or 86400))
        self.REDIS_USE_SSL = os.environ.get("REDIS_USE_SSL", str(self.REDIS_USE_SSL)).lower() in ("1", "true", "yes")
        self.REDIS_SSL_CERT_REQS = os.environ.get("REDIS_SSL_CERT_REQS", self.REDIS_SSL_CERT_REQS)

    def _log_missing_sensitive_fields(self):
        sensitive_fields = [
            "REDIS_HOST",
            "REDIS_PORT",
            "REDIS_PASSWORD",
            "REDIS_DB",
            "REDIS_USE_SSL",
            "REDIS_SSL_CERT_REQS"
        ]
        for field in sensitive_fields:
            value = getattr(self, field, None)
            valid, msg = _validate_env_var(field, value)
            if not valid:
                logger.warning(msg)
            elif msg:
                logger.warning(msg)

    def validate_required_fields(self):
        required_fields = [
            "REDIS_HOST",
            "REDIS_PORT",
            "REDIS_PASSWORD",
            "REDIS_DB",
            "REDIS_USE_SSL",
            "REDIS_SSL_CERT_REQS"
        ]
        missing = []
        for field in required_fields:
            value = getattr(self, field, None)
            valid, _ = _validate_env_var(field, value)
            if not valid:
                missing.append(field)
        if missing:
            raise ValueError(f"Os seguintes campos obrigatórios estão vazios após o carregamento dos segredos: {', '.join(missing)}")

    def validate_vault_configuration(self):
        vault_env_vars = [
            ("AZURE_KV_URL", self.AZURE_KV_URL),
            ("DEVOPS_KV_URL", self.DEVOPS_KV_URL),
            ("GITHUB_KV_URL", self.GITHUB_KV_URL),
            ("LLM_KV_URL", self.LLM_KV_URL)
        ]
        missing = [name for name, val in vault_env_vars if not val]
        if missing:
            raise EnvironmentError(f"As seguintes variáveis de ambiente de URL de Key Vault estão ausentes: {', '.join(missing)}")
        for name, url in vault_env_vars:
            if not url.startswith("https://"):
                raise EnvironmentError(f"A URL do Key Vault '{name}' é inválida: {url}")

    def load_secrets_from_vault(self, vault_type: VaultType):
        manager = AzureSecretManager(vault_type=vault_type)
        if vault_type == VaultType.LLM:
            anthropic_key = manager.get_secret("ANTHROPICAPIKEY")
            openai_modelos = manager.get_secret("azure-openai-modelos")
            return {"ANTHROPICAPIKEY": anthropic_key, "azure-openai-modelos": openai_modelos}
        return {}

    def get_secret_manager(self, vault_type: str) -> AzureSecretManager:
        try:
            vt_enum = VaultType(vault_type)
        except ValueError:
            raise ValueError(f"Tipo de Key Vault inválido: {vault_type}. Esperado: 'azure', 'devops', 'github', 'llm'.")
        return AzureSecretManager(vault_type=vt_enum)

settings = Settings()
