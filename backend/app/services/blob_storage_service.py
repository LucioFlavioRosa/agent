import io
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, status
from azure.storage.blob import BlobServiceClient, ContentSettings
from backend.app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

def _get_blob_clients():
    """
    Inicializa BlobServiceClient e ContainerClient sob demanda (lazy loading).
    Valida se a connection string está presente.
    """
    connection_string = getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None)
    if not connection_string:
        # Loga erro crítico pois isso impede o funcionamento do sistema
        logger.critical("Tentativa de upload sem AZURE_STORAGE_CONNECTION_STRING configurada.")
        raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING não está configurada. Certifique-se de que o segredo foi carregado do Azure Key Vault corretamente.")
    
    container_name = getattr(settings, "AZURE_STORAGE_CONTAINER_NAME", "arquivos")
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)
    return blob_service_client, container_client

def _sync_upload(file_bytes: bytes, blob_folder: str, blob_filename: str):
    """
    Função síncrona executada em background.
    OBS: Não lançamos HTTPException aqui pois a resposta já foi enviada ao cliente.
    Devemos logar o erro para monitoramento.
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
            # Mantendo seu hardcode para DOCX conforme seu snippet
            content_settings=ContentSettings(content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        )
        logger.info(f"Upload concluído com sucesso: {blob_client.url}")
        
    except Exception as e:
        # CRÍTICO: Logar o erro completo, pois o usuário não verá o 500
        logger.error(f"FALHA NO UPLOAD BACKGROUND ({blob_filename}): {str(e)}", exc_info=True)
        # Sugestão futura: Atualizar status em um banco de dados para "Erro"

async def upload_docx_to_blob_helper(file: UploadFile, blob_folder: str, blob_filename: str, background_tasks: BackgroundTasks) -> str:
    """
    Helper que orquestra a leitura e o agendamento.
    """
    # 1. Leitura Preventiva (Evita erro de arquivo fechado)
    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao ler arquivo: {str(e)}")

    # 2. Agendamento
    background_tasks.add_task(
        _sync_upload, 
        file_bytes=file_bytes, 
        blob_folder=blob_folder, 
        blob_filename=blob_filename
    )
    
    # 3. Geração de URL (Previsão otimista)
    # Não precisamos reconectar ao Azure só para gerar a URL se soubermos o padrão,
    # mas reutilizar _get_blob_clients é mais seguro para garantir a URL base correta.
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
    """
    Endpoint público que utiliza sua lógica de upload.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nome do arquivo inválido.")

    # Usa sua função helper
    try:
        # Define um nome de blob seguro (pode usar UUID aqui se quiser evitar colisão)
        blob_url = await upload_docx_to_blob_helper(
            file=file,
            blob_folder=folder,
            blob_filename=file.filename,
            background_tasks=background_tasks
        )
    except RuntimeError as re:
        # Captura erro de configuração (Key Vault) e retorna 500 limpo
        raise HTTPException(status_code=500, detail=str(re))

    return {
        "message": "Upload iniciado em background.",
        "filename": file.filename,
        "url_estimada": blob_url,
        "status": "processing"
    }
