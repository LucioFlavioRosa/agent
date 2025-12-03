import logging
import os
from backend.app.core.config import settings
from backend.app.services.azure_secret_manager import AzureSecretManager, VaultType
from backend.app.services.blob_storage_service import BlobServiceClient
from backend.app.services.project_state_service import ProjectStateService
import httpx
import redis
import asyncio

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
                'detail': f"Segredos não carregados: {', '.join(missing)}"
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
            self.logger.info("Validando Blob Storage usando connection string carregada do Key Vault 'kv-codeai-azure-dev-usc'.")
            if not conn_str:
                raise ValueError("Connection string do Blob Storage não configurada.")
            blob_service_client = BlobServiceClient.from_connection_string(conn_str)
            container_client = blob_service_client.get_container_client(container_name)
            _ = list(container_client.list_blobs(name_starts_with=None, results_per_page=1))
            test_usuario = os.environ.get("TEST_EXISTING_USER", "test_user_validator")
            test_projeto = os.environ.get("TEST_EXISTING_PROJECT", "test_project_validator")
            blob_folder = f"{test_usuario}/{test_projeto}/estados"
            blobs = list(container_client.list_blobs(name_starts_with=blob_folder + "/"))
            if blobs:
                self.status_report['blob_storage'] = {
                    'status': 'ok',
                    'detail': 'Conexão com Blob Storage bem-sucedida e blobs de projetos existentes encontrados.'
                }
            else:
                self.status_report['blob_storage'] = {
                    'status': 'ok',
                    'detail': 'Conexão com Blob Storage bem-sucedida, mas nenhum projeto existente encontrado para teste.'
                }
            # Validação adicional: busca de metadados do projeto existente
            try:
                metadata = None
                # Chamada direta ao ProjectStateService.load_latest_state_from_blob (async para sync)
                metadata = asyncio.run(ProjectStateService.load_latest_state_from_blob(test_usuario, test_projeto))
                if metadata and metadata.get("analysis_type"):
                    self.status_report['blob_storage_metadata'] = {
                        'status': 'ok',
                        'detail': 'Metadados e analysis_type recuperados com sucesso do estado mais recente do projeto.'
                    }
                else:
                    self.status_report['blob_storage_metadata'] = {
                        'status': 'fail',
                        'detail': 'Metadados analysis_name e analysis_type não encontrados no estado mais recente do projeto.'
                    }
            except Exception as e:
                self.status_report['blob_storage_metadata'] = {
                    'status': 'fail',
                    'detail': f'Erro ao buscar metadados do projeto existente: {e}'
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
            host = getattr(settings, 'REDIS_HOST', None)
            port = getattr(settings, 'REDIS_PORT', None)
            password = getattr(settings, 'REDIS_PASSWORD', None)
            db = getattr(settings, 'REDIS_DB', None)
            use_ssl = getattr(settings, 'REDIS_USE_SSL', None)
            ssl_cert_reqs = getattr(settings, 'REDIS_SSL_CERT_REQS', None)
            missing = []
            if not host:
                missing.append('REDIS_HOST')
            if not port:
                missing.append('REDIS_PORT')
            if not password:
                missing.append('REDIS_PASSWORD')
            if db is None:
                missing.append('REDIS_DB')
            if use_ssl is None:
                missing.append('REDIS_USE_SSL')
            if ssl_cert_reqs is None:
                missing.append('REDIS_SSL_CERT_REQS')
            if missing:
                self.status_report['redis'] = {
                    'status': 'fail',
                    'detail': f"Segredos do Redis não carregados do Key Vault: {', '.join(missing)}"
                }
                self.logger.error(f"Redis secrets missing: {missing}")
                return
            client = redis.Redis(
                host=host,
                port=int(port),
                password=password,
                db=int(db),
                ssl=use_ssl,
                ssl_cert_reqs=ssl_cert_reqs,
                socket_connect_timeout=5,
                socket_timeout=5,
                decode_responses=True
            )
            client.ping()
            self.status_report['redis'] = {
                'status': 'ok',
                'detail': 'Conexão com Redis via endpoint privado e SSL bem-sucedida.'
            }
        except Exception as e:
            self.status_report['redis'] = {
                'status': 'fail',
                'detail': f'Erro ao conectar ao Redis (endpoint privado): {e}'
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
