import io
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, status
from azure.storage.blob import BlobServiceClient, ContentSettings
from backend.app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

def _get_blob_clients():
    connection_string = getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None)
    logger.info(f"Blob Storage Connection String carregado: {'SET' if connection_string else 'NOT SET'} (Origem: Key Vault 'kv-codeai-azure-dev-usc', segredo: 'azure-storage-connection-string')")
    if not connection_string:
        logger.critical("Tentativa de upload sem AZURE_STORAGE_CONNECTION_STRING configurada.")
        raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING não está configurada. Certifique-se de que o segredo foi carregado do Azure Key Vault corretamente.")
    container_name = getattr(settings, "AZURE_STORAGE_CONTAINER_NAME", "arquivos")
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)
    return blob_service_client, container_client

def _sync_upload(file_bytes: bytes, blob_folder: str, blob_filename: str):
    try:
        _, container_client = _get_blob_clients()
        blob_path = f"{blob_folder}/{blob_filename}"
        blob_client = container_client.get_blob_client(blob_path)
        file_stream = io.BytesIO(file_bytes)
        logger.info(f"Iniciando upload background: {blob_path}")
        blob_client.upload_blob(
            file_stream,
            overwrite=True,
            content_settings=ContentSettings(content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        )
        logger.info(f"Upload concluído com sucesso: {blob_client.url}")
    except Exception as e:
        logger.error(f"FALHA NO UPLOAD BACKGROUND ({blob_filename}): {str(e)}", exc_info=True)

async def upload_docx_to_blob_helper(file: UploadFile, blob_folder: str, blob_filename: str, background_tasks: BackgroundTasks) -> str:
    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao ler arquivo: {str(e)}")
    background_tasks.add_task(
        _sync_upload, 
        file_bytes=file_bytes, 
        blob_folder=blob_folder, 
        blob_filename=blob_filename
    )
    _, container_client = _get_blob_clients()
    blob_path = f"{blob_folder}/{blob_filename}"
    blob_client = container_client.get_blob_client(blob_path)
    return blob_client.url

@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    folder: str = "uploads"
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nome do arquivo inválido.")
    try:
        blob_url = await upload_docx_to_blob_helper(
            file=file,
            blob_folder=folder,
            blob_filename=file.filename,
            background_tasks=background_tasks
        )
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    return {
        "message": "Upload iniciado em background.",
        "filename": file.filename,
        "url_estimada": blob_url,
        "status": "processing"
    }
