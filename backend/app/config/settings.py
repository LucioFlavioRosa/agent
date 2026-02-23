from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    AZURE_KEYVAULT_INFRASTRUCTURE_URL: str = Field(..., env="AZURE_KEYVAULT_INFRASTRUCTURE_URL")
    AZURE_KEYVAULT_LLM_URL: str = Field(..., env="AZURE_KEYVAULT_LLM_URL")
    AZURE_KEYVAULT_INTEGRATIONS_URL: str = Field(..., env="AZURE_KEYVAULT_INTEGRATIONS_URL")
    AZURE_STORAGE_QUEUE_CONNECTION_STRING: str = Field(..., env="AZURE_STORAGE_QUEUE_CONNECTION_STRING")

    class Config:
        case_sensitive = True

settings = Settings()
