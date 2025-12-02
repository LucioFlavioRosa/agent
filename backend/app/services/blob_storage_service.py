import io
import logging
from fastapi import UploadFile, HTTPException, BackgroundTasks
from azure.storage.blob import BlobServiceClient, ContentSettings
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

def _get_blob_clients():
    """
    Função auxiliar interna para criar clientes do Azure Blob Storage.
    """
    connection_string = getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None)
    
    # Log de segurança (sem expor a string completa)
    status_conn = 'SET' if connection_string else 'NOT SET'
    logger.info(f"Blob Storage Connection String carregado: {status_conn} (Origem: Key Vault)")
    
    if not connection_string:
        logger.critical("Tentativa de upload sem AZURE_STORAGE_CONNECTION_STRING configurada.")
        raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING não está configurada. Verifique o Key Vault.")
        
    container_name = getattr(settings, "AZURE_STORAGE_CONTAINER_NAME", "arquivos")
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)
    return blob_service_client, container_client

def _sync_upload(file_bytes: bytes, blob_folder: str, blob_filename: str):
    """
    Função síncrona que será executada em background para não travar a API.
    """
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
    """
    Prepara o arquivo e agenda o upload em background. Retorna a URL estimada.
    """
    try:
        # Lê os bytes antes de passar para a task background (pois o UploadFile pode fechar)
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao ler arquivo: {str(e)}")
    
    # Agenda a tarefa pesada para rodar depois da resposta
    background_tasks.add_task(
        _sync_upload, 
        file_bytes=file_bytes, 
        blob_folder=blob_folder, 
        blob_filename=blob_filename
    )
    
    # Gera a URL para retornar imediatamente ao usuário
    _, container_client = _get_blob_clients()
    blob_path = f"{blob_folder}/{blob_filename}"
    blob_client = container_client.get_blob_client(blob_path)
    
    return blob_client.url
