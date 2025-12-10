import os
from azure.storage.blob import BlobServiceClient
from tools.azure_secret_manager import AzureSecretManager
from tools.blob_report_path_builder import build_report_blob_path

def read_report_from_blob(projeto: str, analysis_type: str, repository_type: str, repo_name: str, branch_name: str, analysis_name: str) -> str:
    container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME')
    if not container_name:
        raise RuntimeError('Azure Blob Storage container name missing.')
    connection_string = None
    secret_name = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    try:
        secret_manager = AzureSecretManager()
        connection_string = secret_manager.get_secret(secret_name)
    except Exception as e:
        print(f"Warning: Failed to get connection string from Key Vault: {e}")
        connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    if not connection_string:
        raise RuntimeError('Azure Blob Storage connection string not found in Key Vault or environment variables.')
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
