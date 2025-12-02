import logging
import os
from backend.app.core.config import settings
from backend.app.services.azure_secret_manager import AzureSecretManager, VaultType
from backend.app.services.blob_storage_service import BlobServiceClient
import httpx
import redis

class StartupValidator:
    def __init__(self):
        self.status_report = {}
        self.logger = logging.getLogger("StartupValidator")

    def validate_key_vault(self):
        try:
            manager = AzureSecretManager(vault_type=VaultType.AZURE)
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

    def validate_redis_connection(self):
        try:
            redis_host = getattr(settings, 'REDIS_HOST', None)
            redis_port = int(getattr(settings, 'REDIS_PORT', 6379))
            redis_password = getattr(settings, 'REDIS_PASSWORD', None)
            redis_db = int(getattr(settings, 'REDIS_DB', 0))
            redis_use_ssl = getattr(settings, 'REDIS_USE_SSL', True)
            redis_ssl_cert_reqs = getattr(settings, 'REDIS_SSL_CERT_REQS', 'required')
            client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                db=redis_db,
                ssl=redis_use_ssl,
                ssl_cert_reqs=redis_ssl_cert_reqs,
                decode_responses=True
            )
            client.ping()
            self.status_report['redis'] = {
                'status': 'ok',
                'detail': 'Conexão com Redis via endpoint privado e SSL/TLS bem-sucedida.'
            }
        except Exception as e:
            self.status_report['redis'] = {
                'status': 'fail',
                'detail': f'Erro ao conectar ao Redis via endpoint privado: {e}'
            }
            self.logger.error(f"Redis connection validation failed: {e}")

    def validate_all_configs(self):
        self.status_report = {}
        self.validate_key_vault()
        self.validate_secrets_loaded()
        self.validate_blob_storage()
        self.validate_mcp_server()
        self.validate_redis_connection()
        return self.status_report
