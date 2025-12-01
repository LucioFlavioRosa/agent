import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Request
from pydantic import BaseModel

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
    session_id: str

@router.post("/docx", response_model=UploadDocxResponse, tags=["Upload"])
async def upload_docx(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    projeto: str = Form(...),
    analysis_name: str = Form(...),
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
    blob_filename = f"{analysis_name}.docx"

    session_service = RedisSessionService()
    session_id = session_service.create_session(
        usuario_executor=usuario_executor,
        projeto=projeto,
        analysis_name=analysis_name,
        analysis_type='upload'
    )
    session_service.add_step(
        session_id=session_id,
        action='upload_initiated',
        status='processing',
        metadata={'filename': file.filename}
    )

    try:
        blob_url = await upload_docx_to_blob(file, blob_folder, blob_filename, background_tasks)
    except ValueError as ve:
        logger.error(f"Erro de configuração do Blob Storage: {ve}")
        raise HTTPException(status_code=503, detail="Serviço de armazenamento temporariamente indisponível")
    except Exception as e:
        logger.error(f"Erro inesperado no Blob Storage: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo: {str(e)}")

    return UploadDocxResponse(
        blob_url=blob_url,
        extracted_text=texto_extraido,
        message="Arquivo processado com sucesso. Pronto para análise.",
        session_id=session_id
    )
