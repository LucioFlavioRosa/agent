import os
from azure.storage.blob import BlobServiceClient, ContentSettings

def upload_report_to_blob(report_text: str, analysis_name: str) -> str:
    connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME')
    if not connection_string or not container_name:
        raise RuntimeError('Azure Blob Storage connection info missing.')

    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=f"reports/{analysis_name}.md")
    blob_client.upload_blob(report_text, overwrite=True, content_settings=ContentSettings(content_type='text/markdown'))
    return blob_client.url