import logging
import os
from backend.app.core.config import settings
from backend.app.services.azure_secret_manager import AzureSecretManager, VaultType
from backend.app.services.blob_storage_service import BlobServiceClient
import httpx

class StartupValidator:
    """
    Serviço que centraliza validações críticas de inicialização:
    - Key Vault acessível
    - Segredos carregados
    - Blob Storage conectável
    - MCP Server respondendo
    """
    def __init__(self):
        self.status_report = {}
        self.logger = logging.getLogger("StartupValidator")

    def validate_key_vault(self):
        try:
            # Tenta instanciar e buscar um segredo simples usando hífens no nome
            manager = AzureSecretManager(vault_type=VaultType.AZURE)
            # O nome do segredo no Azure Key Vault deve usar hífens, não underscores
            secret = manager.get_secret("azure-storage-connection-string")
            self.status_report['key_vault'] = {
                'status': 'ok',
                'detail': 'Key Vault acessível e segredo lido com sucesso.'
            }
        except Exception as e:
            self.status_report['key_vault'] = {
                'status': 'fail',
                'detail': f'Erro ao acessar Key Vault: {e}'
            }
            self.logger.error(f"Key Vault validation failed: {e}")

    def validate_secrets_loaded(self):
        required = [
            'AZURE_STORAGE_CONNECTION_STRING',
            'AZURE_AD_CLIENT_SECRET',
            'JWT_SECRET_KEY'
        ]
        missing = [k for k in required if not getattr(settings, k, None)]
        if missing:
            self.status_report['secrets'] = {
                'status': 'fail',
                'detail': f'Segredos não carregados: {', '.join(missing)}'
            }
            self.logger.error(f"Secrets missing: {missing}")
        else:
            self.status_report['secrets'] = {
                'status': 'ok',
                'detail': 'Todos os segredos necessários estão carregados.'
            }

    def validate_blob_storage(self):
        try:
            conn_str = getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None)
            container_name = getattr(settings, "AZURE_STORAGE_CONTAINER_NAME", "arquivos")
            if not conn_str:
                raise ValueError("Connection string do Blob Storage não configurada.")
            blob_service_client = BlobServiceClient.from_connection_string(conn_str)
            container_client = blob_service_client.get_container_client(container_name)
            # Tenta listar blobs para validar conexão
            _ = list(container_client.list_blobs(name_starts_with=None, results_per_page=1))
            self.status_report['blob_storage'] = {
                'status': 'ok',
                'detail': 'Conexão com Blob Storage bem-sucedida.'
            }
        except Exception as e:
            self.status_report['blob_storage'] = {
                'status': 'fail',
                'detail': f'Erro ao conectar ao Blob Storage: {e}'
            }
            self.logger.error(f"Blob Storage validation failed: {e}")

    def validate_mcp_server(self):
        try:
            url = getattr(settings, "MCP_SERVER_BASE_URL", None)
            if not url:
                raise ValueError("MCP_SERVER_BASE_URL não configurada.")
            url = url.rstrip('/') + '/health'
            with httpx.Client(timeout=5) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    self.status_report['mcp_server'] = {
                        'status': 'ok',
                        'detail': 'MCP Server respondeu com sucesso.'
                    }
                else:
                    self.status_report['mcp_server'] = {
                        'status': 'fail',
                        'detail': f'MCP Server respondeu com status {resp.status_code}.'
                    }
        except Exception as e:
            self.status_report['mcp_server'] = {
                'status': 'fail',
                'detail': f'Erro ao conectar ao MCP Server: {e}'
            }
            self.logger.error(f"MCP Server validation failed: {e}")

    def validate_all_configs(self):
        """
        Executa todas as validações e retorna um relatório detalhado.
        """
        self.status_report = {}
        self.validate_key_vault()
        self.validate_secrets_loaded()
        self.validate_blob_storage()
        self.validate_mcp_server()
        return self.status_report
