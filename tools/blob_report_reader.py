import os
from azure.storage.blob import BlobServiceClient
from tools.azure_secret_manager import AzureSecretManager, VaultType
from tools.blob_report_path_builder import build_report_blob_path
from tools.blob_storage_utils import get_blob_connection_string

def read_report_from_blob(projeto: str, analysis_type: str, repository_type: str, repo_name: str, branch_name: str, analysis_name: str, user_email: str, group_resolver: object = None) -> str:
    container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME')
    if not container_name:
        raise RuntimeError('Azure Blob Storage container name missing.')
    # Instancia o AzureSecretManager com VaultType.AZURE_INFRASTRUCTURE para ler secrets de infraestrutura
    secret_manager = AzureSecretManager(vault_type=VaultType.AZURE_INFRASTRUCTURE)
    connection_string = get_blob_connection_string(secret_manager, user_email, group_resolver)
    blob_path = build_report_blob_path(projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name)
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_path)
    try:
        blob_data = blob_client.download_blob()
        report_content = blob_data.readall().decode('utf-8')
        print(f"[blob_report_reader] Relatório encontrado no blob: {blob_path} (tamanho: {len(report_content)})")
        return report_content
    except Exception as e:
        error_str = str(e)
        if "BlobNotFound" in error_str or "404" in error_str:
            print(f"[blob_report_reader] Report not found in blob storage: {blob_path}")
            return None
        print(f"[blob_report_reader] Erro ao tentar ler blob {blob_path}: {e}")
        raise
