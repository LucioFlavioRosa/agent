import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Optional

from ..middleware.auth_middleware import get_current_user, _extract_usuario_executor
from ..services.blob_storage_service import upload_and_extract_docx
from ..services.redis_session_service import RedisSessionService
from ..models.docx_models import UploadDocxResponse

router = APIRouter()
logger = logging.getLogger("upload_api")

@router.post("/docx", response_model=UploadDocxResponse, tags=["Upload"])
async def upload_docx(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    projeto: str = Form(...),
    analysis_type: str = Form(...),
    comentario_usuario: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    usuario_executor = _extract_usuario_executor(current_user)
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Apenas arquivos .docx são permitidos.")
    try:
        blob_folder = f"{usuario_executor}/{projeto}/arquivos_recebidos/docx"
        blob_filename = f"{analysis_type}.docx"
        blob_url, texto_extraido = await upload_and_extract_docx(file, blob_folder, blob_filename, background_tasks)
    except ValueError as ve:
        logger.error(f"Erro de configuração do Blob Storage: {ve}")
        raise HTTPException(status_code=503, detail="Serviço de armazenamento temporariamente indisponível")
    except Exception as e:
        logger.error(f"Erro inesperado no Blob Storage ou extração: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo ou extrair texto: {str(e)}")
    redis_service = RedisSessionService()
    session_id = redis_service.create_session(
        usuario_executor,
        projeto,
        analysis_type,
        comentario_usuario=comentario_usuario,
        extracted_text=texto_extraido
    )
    try:
        redis_service.add_docx_file(session_id, blob_url)
    except Exception as e:
        logger.error(f"Erro ao adicionar arquivo DOCX à sessão: {e}")
    try:
        redis_service.update_session_extracted_text(session_id, texto_extraido)
    except Exception as e:
        logger.error(f"Erro ao salvar texto extraído na sessão: {e}")
    mensagem = "Arquivo processado com sucesso. Pronto para análise. (Upload opcional para projetos existentes)"
    return UploadDocxResponse(
        blob_url=blob_url,
        extracted_text=texto_extraido,
        message=mensagem,
        session_id=session_id,
        job_id=session_id
    )
