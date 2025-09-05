import os
from azure.storage.blob import BlobServiceClient, ContentSettings
from tools.azure_secret_manager import AzureSecretManager

def upload_report_to_blob(report_text: str, analysis_name: str) -> str:
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
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=f"reports/{analysis_name}.md")
    blob_client.upload_blob(report_text, overwrite=True, content_settings=ContentSettings(content_type='text/markdown'))
    return blob_client.url
