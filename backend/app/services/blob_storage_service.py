import os
from azure.storage.blob import BlobServiceClient, ContentSettings
from fastapi import UploadFile, HTTPException, BackgroundTasks

AZURE_BLOB_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING")
AZURE_BLOB_CONTAINER = os.getenv("AZURE_BLOB_CONTAINER", "arquivos")
blob_service_client = BlobServiceClient.from_connection_string(AZURE_BLOB_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(AZURE_BLOB_CONTAINER)

def _sync_upload(file: UploadFile, blob_folder: str, blob_filename: str) -> str:
    try:
        blob_path = f"{blob_folder}/{blob_filename}"
        blob_client = container_client.get_blob_client(blob_path)
        file.file.seek(0)
        blob_client.upload_blob(
            file.file,
            overwrite=True,
            content_settings=ContentSettings(content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        )
        return blob_client.url
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao fazer upload do arquivo para o Blob Storage: {str(e)}")

async def upload_docx_to_blob(file: UploadFile, blob_folder: str, blob_filename: str, background_tasks: BackgroundTasks) -> str:
    """
    Faz upload do arquivo docx para o Azure Blob Storage no caminho correto e retorna a URL pública do blob. O upload é executado em background.
    """
    def upload_task():
        _sync_upload(file, blob_folder, blob_filename)
    background_tasks.add_task(upload_task)
    # Retorna a URL do blob antes do upload terminar (padrão FastAPI para tasks)
    blob_path = f"{blob_folder}/{blob_filename}"
    blob_client = container_client.get_blob_client(blob_path)
    return blob_client.url
