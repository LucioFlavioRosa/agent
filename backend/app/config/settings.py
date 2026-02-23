from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """
    Configurações principais do MCP.
    - AZURE_INFRA_VAULT_URL: URL do cofre de infraestrutura.
    - AZURE_LLM_VAULT_URL: URL do cofre de LLM.
    - AZURE_PROJECTS_VAULT_URL: URL do cofre de projetos.
    - QUEUE_NAME: Nome da fila para processamento.
    - BLOB_UPLOAD_MAX_SIZE_MB: Limite máximo de tamanho do upload de arquivo (MB).
    - BLOB_ALLOWED_EXTENSIONS: Extensões permitidas para upload de documentos (ex: .docx,.pdf,.txt).
    """
    AZURE_INFRA_VAULT_URL: str = Field(..., env="AZURE_INFRA_VAULT_URL")
    AZURE_LLM_VAULT_URL: str = Field(..., env="AZURE_LLM_VAULT_URL")
    AZURE_PROJECTS_VAULT_URL: str = Field(..., env="AZURE_PROJECTS_VAULT_URL")
    QUEUE_NAME: str = Field("mcp-tasks-queue", env="QUEUE_NAME")
    BLOB_UPLOAD_MAX_SIZE_MB: int = Field(100, env="BLOB_UPLOAD_MAX_SIZE_MB")
    BLOB_ALLOWED_EXTENSIONS: str = Field(".docx,.pdf,.txt", env="BLOB_ALLOWED_EXTENSIONS")

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
