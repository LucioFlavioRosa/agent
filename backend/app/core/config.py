from pydantic_settings import BaseSettings
from typing import Dict, Optional
from backend.app.services.azure_secret_manager import AzureSecretManager, VaultType
import logging

class Settings(BaseSettings):
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_STORAGE_CONTAINER_NAME: str = ""
    MCP_SERVER_BASE_URL: str = "http://mcp-app-service.azurewebsites.net"

    # Novos campos para Azure AD (moderno, sem ROPC)
    AZURE_AD_TENANT_ID: str = ""
    AZURE_AD_CLIENT_ID: str = ""
    AZURE_AD_CLIENT_SECRET: str = ""
    
    # Novos campos para validação JWT segura
    AZURE_AD_JWKS_URI: Optional[str] = None  # Ex: https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys
    AZURE_AD_ISSUER: Optional[str] = None    # Ex: https://login.microsoftonline.com/{tenant_id}/v2.0
    AZURE_AD_AUDIENCE: Optional[str] = None  # Geralmente o client_id da API registrada no Azure AD

    # Mapeamento de analysis_type para endpoints MCP
    MCP_ENDPOINTS: Dict[str, str] = {
        "criacao_epicos_azure_devops": "https://mcp-epicos.azurewebsites.net"
        # Adicione outros mapeamentos conforme necessário
    }
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def __init__(self, **values):
        super().__init__(**values)
        # Preenche automaticamente os campos JWKS/ISSUER/AUDIENCE se não definidos
        if not self.AZURE_AD_JWKS_URI and self.AZURE_AD_TENANT_ID:
            self.AZURE_AD_JWKS_URI = f"https://login.microsoftonline.com/{self.AZURE_AD_TENANT_ID}/discovery/v2.0/keys"
        if not self.AZURE_AD_ISSUER and self.AZURE_AD_TENANT_ID:
            self.AZURE_AD_ISSUER = f"https://login.microsoftonline.com/{self.AZURE_AD_TENANT_ID}/v2.0"
        if not self.AZURE_AD_AUDIENCE and self.AZURE_AD_CLIENT_ID:
            self.AZURE_AD_AUDIENCE = self.AZURE_AD_CLIENT_ID
        # Validação dos campos sensíveis (apenas loga aviso, não lança erro)
        self._log_missing_sensitive_fields()

    def _log_missing_sensitive_fields(self):
        logger = logging.getLogger("Settings")
        # Os nomes dos campos sensíveis devem ser os nomes dos atributos do objeto settings (com underscores)
        sensitive_fields = [
            "AZURE_STORAGE_CONNECTION_STRING",
            "AZURE_STORAGE_CONTAINER_NAME",
            "AZURE_AD_CLIENT_SECRET",
            "JWT_SECRET_KEY",
            "MCP_SERVER_BASE_URL"
        ]
        for field in sensitive_fields:
            value = getattr(self, field, None)
            if not value:
                logger.warning(f"[Settings] Campo sensível '{field}' está vazio após inicialização. Ele será preenchido após o carregamento dos segredos.")
                # Adicional: alerta se o nome do campo não está alinhado com padrão Azure Key Vault (hífens)
                if '_' in field:
                    logger.warning(f"[Settings] Atenção: O nome do segredo '{field}' contém underscores. No Azure Key Vault, utilize hífens: '{field.lower().replace('_', '-')}'.")

    def validate_required_fields(self):
        """
        Verifica se campos críticos estão preenchidos após o carregamento dos segredos.
        Lança ValueError se algum campo obrigatório estiver vazio.
        """
        # Os nomes dos campos obrigatórios devem ser os nomes dos atributos do objeto settings (com underscores)
        required_fields = [
            "AZURE_STORAGE_CONNECTION_STRING",
            "AZURE_STORAGE_CONTAINER_NAME",
            "AZURE_AD_CLIENT_SECRET",
            "JWT_SECRET_KEY",
            "MCP_SERVER_BASE_URL"
        ]
        missing = [field for field in required_fields if not getattr(self, field, None)]
        if missing:
            raise ValueError(f"Os seguintes campos obrigatórios estão vazios após o carregamento dos segredos: {', '.join(missing)}")

    def get_secret_manager(self, vault_type: str) -> AzureSecretManager:
        """
        Retorna uma instância do AzureSecretManager configurada para o cofre correto.
        Args:
            vault_type: Tipo do cofre ('azure', 'devops', 'github', 'llm')
        Returns:
            AzureSecretManager: Instância pronta para uso
        Raises:
            ValueError: Se o tipo for inválido
        """
        try:
            vt_enum = VaultType(vault_type)
        except ValueError:
            raise ValueError(f"Tipo de Key Vault inválido: {vault_type}. Esperado: 'azure', 'devops', 'github', 'llm'.")
        return AzureSecretManager(vault_type=vt_enum)

settings = Settings()
