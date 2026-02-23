from pydantic_settings import BaseSettings
from azure.identity import DefaultAzureCredential

class Settings(BaseSettings):
    AZURE_KEYVAULT_INFRASTRUCTURE_URL: str
    AZURE_KEYVAULT_LLM_URL: str
    AZURE_KEYVAULT_PROJECT_TOOLS_URL: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
azure_credential = DefaultAzureCredential()
