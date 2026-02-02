import os
from urllib.parse import urlparse
from azure.storage.blob import BlobServiceClient, ContentSettings
from tools.blob_job_tracker import BlobJobTracker
from tools.azure_secret_manager import AzureSecretManager, VaultType
from tools.blob_report_path_builder import build_report_blob_path
from tools.blob_storage_utils import get_blob_connection_string

class BlobStorageService:
    def __init__(self):
        self._blob_service_client = None
        self._container_name = None
        self._init_blob_service()

    def _init_blob_service(self):
        container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME')
        if not container_name:
            raise RuntimeError('Azure Blob Storage container name missing.')
        # Instancia o secret manager com o cofre específico para blob storage
        secret_manager = AzureSecretManager(vault_type=VaultType.BLOB_STORAGE)
        print(f"[BlobStorageService] DEBUG: Usando VaultType '{VaultType.BLOB_STORAGE.value}' para recuperar connection string do Blob Storage.")
        connection_string = get_blob_connection_string(secret_manager)
        print(f"[BlobStorageService] DEBUG: Connection string recuperada do cofre: {'OK' if connection_string else 'FALHA'}")
        self._blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self._container_name = container_name

    def upload_report(self, report_text, projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name):
        blob_path = build_report_blob_path(projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name)
        blob_client = self._blob_service_client.get_blob_client(container=self._container_name, blob=blob_path)
        blob_client.upload_blob(report_text, overwrite=True, content_settings=ContentSettings(content_type='text/markdown'))
        return blob_client.url

    def read_report(self, projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name):
        blob_path = build_report_blob_path(projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name)
        blob_client = self._blob_service_client.get_blob_client(container=self._container_name, blob=blob_path)
        if not blob_client.exists():
            return None
        return blob_client.download_blob().readall().decode('utf-8')
        
    def get_report_url(self, projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name) -> str:
        """Constrói e retorna a URL de um relatório sem fazer upload."""
        blob_path = build_report_blob_path(projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name)
        blob_client = self._blob_service_client.get_blob_client(container=self._container_name, blob=blob_path)
        return blob_client.url

    def update_job_tracker(self, report_blob_url: str, job_id: str) -> None:
        try:
            path = urlparse(report_blob_url).path
            path_parts = path.lstrip('/').split('/', 1)
            if len(path_parts) != 2:
                print(f"[BlobStorageService] Warning: Could not parse blob path from URL: {report_blob_url}")
                return
            blob_path = path_parts[1]
            tracker_path = BlobJobTracker.build_tracker_blob_path(blob_path)
            BlobJobTracker.append_job_id(self._blob_service_client, self._container_name, tracker_path, job_id)
        except Exception as e:
            print(f"[BlobStorageService] Warning: Failed to update job tracker for {report_blob_url}: {e}")

    def get_jobs_for_report(self, report_blob_url: str):
        try:
            path = urlparse(report_blob_url).path
            path_parts = path.lstrip('/').split('/', 1)
            if len(path_parts) != 2:
                print(f"[BlobStorageService] Warning: Could not parse blob path from URL: {report_blob_url}")
                return []
            blob_path = path_parts[1]
            tracker_path = BlobJobTracker.build_tracker_blob_path(blob_path)
            return BlobJobTracker.read_job_list(self._blob_service_client, self._container_name, tracker_path)
        except Exception as e:
            print(f"[BlobStorageService] Warning: Failed to get jobs for report {report_blob_url}: {e}")
            return []
