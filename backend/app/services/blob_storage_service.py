import os
import io
from azure.storage.blob import BlobServiceClient, ContentSettings
from fastapi import UploadFile, HTTPException, BackgroundTasks
from backend.app.core.config import settings

def _get_blob_clients():
    """
    Inicializa BlobServiceClient e ContainerClient sob demanda (lazy loading).
    Valida se a connection string está presente.
    """
    connection_string = getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None)
    if not connection_string:
        raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING não está configurada. Certifique-se de que o segredo foi carregado do Azure Key Vault corretamente.")
    container_name = getattr(settings, "AZURE_STORAGE_CONTAINER_NAME", "arquivos")
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)
    return blob_service_client, container_client

def _sync_upload(file_bytes: bytes, blob_folder: str, blob_filename: str) -> str:
    try:
        _, container_client = _get_blob_clients()
        blob_path = f"{blob_folder}/{blob_filename}"
        blob_client = container_client.get_blob_client(blob_path)
        file_stream = io.BytesIO(file_bytes)
        blob_client.upload_blob(
            file_stream,
            overwrite=True,
            content_settings=ContentSettings(content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        )
        return blob_client.url
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao fazer upload do arquivo para o Blob Storage: {str(e)}")

async def upload_docx_to_blob(file: UploadFile, blob_folder: str, blob_filename: str, background_tasks: BackgroundTasks) -> str:
    """
    Faz upload do arquivo docx para o Azure Blob Storage no caminho correto e retorna a URL pública do blob. O upload é executado em background.
    Lê o conteúdo do arquivo em memória antes de iniciar a tarefa em background para evitar erro de arquivo fechado.
    """
    file_bytes = await file.read()
    def upload_task():
        _sync_upload(file_bytes, blob_folder, blob_filename)
    background_tasks.add_task(upload_task)
    # Retorna a URL do blob antes do upload terminar (padrão FastAPI para tasks)
    _, container_client = _get_blob_clients()
    blob_path = f"{blob_folder}/{blob_filename}"
    blob_client = container_client.get_blob_client(blob_path)
    return blob_client.url
