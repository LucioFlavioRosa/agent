import os
from azure.storage.blob import BlobServiceClient, ContentSettings
from tools.azure_secret_manager import AzureSecretManager
from tools.blob_report_path_builder import build_report_blob_path

def extract_blob_path_from_url(blob_url: str) -> str:
    """
    Extrai o blob path (caminho relativo dentro do container) de uma URL completa do Azure Blob Storage.
    Exemplo: https://mystorageaccount.blob.core.windows.net/mycontainer/path/to/file.md -> path/to/file.md
    """
    try:
        # Formato esperado: https://<account>.blob.core.windows.net/<container>/<blob_path>
        parts = blob_url.split('/', 4)  # Divide em até 5 partes
        if len(parts) >= 5:
            return parts[4]  # Retorna tudo após o nome do container
        else:
            # Fallback: retorna a URL completa se o formato for inesperado
            print(f"AVISO: Formato de URL inesperado, retornando URL completa como blob_path: {blob_url}")
            return blob_url
    except Exception as e:
        print(f"ERRO ao extrair blob path da URL: {e}. Retornando URL completa.")
        return blob_url

def upload_report_to_blob(report_text: str, projeto: str, analysis_type: str, repository_type: str, repo_name: str, branch_name: str, analysis_name: str) -> tuple[str, str]:
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

    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    
    original_analysis_name = analysis_name
    counter = 1
    
    while True:
        blob_path = build_report_blob_path(projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_path)
        
        try:
            if blob_client.exists():
                analysis_name = f"{original_analysis_name}-{counter}"
                counter += 1
                continue
            else:
                break
        except Exception:
            break
    
    blob_client.upload_blob(report_text, overwrite=True, content_settings=ContentSettings(content_type='text/markdown'))
    blob_url = blob_client.url
    blob_path_extracted = extract_blob_path_from_url(blob_url)
    return blob_url, blob_path_extracted
