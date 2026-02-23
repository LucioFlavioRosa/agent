from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    # As URLs dos cofres virão obrigatoriamente do ambiente
    AZURE_INFRA_VAULT_URL: str = Field(..., env="AZURE_INFRA_VAULT_URL")
    AZURE_LLM_VAULT_URL: str = Field(..., env="AZURE_LLM_VAULT_URL")
    AZURE_PROJECTS_VAULT_URL: str = Field(..., env="AZURE_PROJECTS_VAULT_URL")
    
    # Nome da fila
    QUEUE_NAME: str = Field("mcp-tasks-queue", env="QUEUE_NAME")

    # Campo opcional para base URL pública dos blobs
    BLOB_STORAGE_BASE_URL: Optional[str] = Field(None, env="BLOB_STORAGE_BASE_URL")

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
