import io
import logging
from fastapi import UploadFile, HTTPException, BackgroundTasks
from azure.storage.blob import BlobServiceClient, ContentSettings
from backend.app.core.config import settings
import asyncio
from backend.app.services.docx_parser_service import extract_text_from_docx

logger = logging.getLogger(__name__)

_blob_service_client_singleton = None
_container_client_singleton = None


def _get_blob_clients():
    global _blob_service_client_singleton, _container_client_singleton
    connection_string = getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None)
    status_conn = 'SET' if connection_string else 'NOT SET'
    logger.info(f"Blob Storage Connection String carregado: {status_conn} (Origem: Key Vault)")
    if not connection_string:
        logger.critical("Tentativa de upload sem AZURE_STORAGE_CONNECTION_STRING configurada.")
        raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING não está configurada. Verifique o Key Vault.")
    container_name = getattr(settings, "AZURE_STORAGE_CONTAINER_NAME", "arquivos")
    if _blob_service_client_singleton is None or _container_client_singleton is None:
        _blob_service_client_singleton = BlobServiceClient.from_connection_string(connection_string)
        _container_client_singleton = _blob_service_client_singleton.get_container_client(container_name)
    return _blob_service_client_singleton, _container_client_singleton

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

async def upload_docx_to_blob(file: UploadFile, blob_folder: str, blob_filename: str, background_tasks: BackgroundTasks) -> str:
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

async def upload_and_extract_docx(file: UploadFile, blob_folder: str, blob_filename: str, background_tasks: BackgroundTasks):
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
    blob_url = blob_client.url
    async def extract_text_from_bytes():
        try:
            import tempfile
            from fastapi import UploadFile as FastAPIUploadFile
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(file_bytes)
                tmp.flush()
                tmp.seek(0)
                class DummyUploadFile:
                    def __init__(self, filename, content):
                        self.filename = filename
                        self.file = io.BytesIO(content)
                    async def read(self):
                        self.file.seek(0)
                        return self.file.read()
                dummy_file = DummyUploadFile(blob_filename, file_bytes)
                text = await extract_text_from_docx(dummy_file)
                return text
        except Exception as e:
            logger.error(f"Erro ao extrair texto do docx em paralelo: {e}")
            return ""
    text_task = asyncio.create_task(extract_text_from_bytes())
    extracted_text = await text_task
    return blob_url, extracted_text
