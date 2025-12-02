import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Optional

from ..middleware.auth_middleware import get_current_user
from ..services.blob_storage_service import upload_docx_to_blob
from ..services.docx_parser_service import extract_text_from_docx
from ..services.redis_session_service import RedisSessionService

router = APIRouter()
logger = logging.getLogger("upload_api")

class UploadDocxResponse(BaseModel):
    blob_url: str
    extracted_text: str
    message: str
    session_id: Optional[str] = None

@router.post("/docx", response_model=UploadDocxResponse, tags=["Upload"])
async def upload_docx(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    projeto: str = Form(...),
    analysis_type: str = Form(...),
    comentario_usuario: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    usuario_executor = current_user.get("usuario_executor") or current_user.get("sub")
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Apenas arquivos .docx são permitidos.")
    try:
        texto_extraido = await extract_text_from_docx(file)
        await file.seek(0)
    except Exception as e:
        logger.error(f"Erro ao extrair texto: {e}")
        raise HTTPException(status_code=400, detail=f"Erro ao processar o arquivo DOCX: {str(e)}")
    blob_folder = f"{usuario_executor}/{projeto}/arquivos_recebidos/docx"
    blob_filename = f"{analysis_type}.docx"
    try:
        blob_url = await upload_docx_to_blob(file, blob_folder, blob_filename, background_tasks)
    except ValueError as ve:
        logger.error(f"Erro de configuração do Blob Storage: {ve}")
        raise HTTPException(status_code=503, detail="Serviço de armazenamento temporariamente indisponível")
    except Exception as e:
        logger.error(f"Erro inesperado no Blob Storage: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo: {str(e)}")
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
    mensagem = "Arquivo processado com sucesso. Pronto para análise."
    return UploadDocxResponse(
        blob_url=blob_url,
        extracted_text=texto_extraido,
        message=mensagem,
        session_id=session_id
    )
