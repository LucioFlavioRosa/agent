from pydantic import BaseSettings

class Settings(BaseSettings):
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    AZURE_STORAGE_CONNECTION_STRING: str
    AZURE_STORAGE_CONTAINER_NAME: str
    MCP_SERVER_BASE_URL: str = "http://mcp-app-service.azurewebsites.net"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
