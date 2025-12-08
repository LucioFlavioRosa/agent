import logging
from fastapi import APIRouter, HTTPException, Depends, Body, BackgroundTasks, UploadFile, File, Form, Request
from pydantic import BaseModel
from typing import Optional

from ..middleware.auth_middleware import get_current_user, _extract_usuario_executor
from ..services.mcp_client_service import MCPClientService
from ..services.redis_session_service import RedisSessionService
from ..services.project_state_service import ProjectStateService
from ..services.blob_storage_service import upload_docx_to_blob
from ..services.docx_parser_service import extract_text_from_docx

import uuid

router = APIRouter()
logger = logging.getLogger("analysis_api")

class StartAnalysisResponse(BaseModel):
    message: str
    project_id: str
    nome_projeto: Optional[str] = None

@router.post("/start", response_model=StartAnalysisResponse, tags=["Analysis"])
async def start_analysis(
    request: Request,
    background_tasks: BackgroundTasks,
    nome_projeto: str = Form(...),
    analysis_type: str = Form(...),
    comentario_extra: Optional[str] = Form(None),
    arquivo_docx: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    usuario_executor = _extract_usuario_executor(current_user)
    logger.info(f"Iniciando análise para projeto '{nome_projeto}' (analysis_type: '{analysis_type}') para usuário {usuario_executor}")
    redis_service = RedisSessionService()
    project_id_final = await ProjectStateService._get_project_id_by_name(usuario_executor, nome_projeto)
    project_state = None
    if project_id_final:
        project_state = await ProjectStateService.load_latest_state_from_blob(usuario_executor, project_id=project_id_final)
    else:
        project_id_final = str(uuid.uuid4())
    texto_extraido = None
    blob_url = None
    if arquivo_docx is not None:
        try:
            texto_extraido = await extract_text_from_docx(arquivo_docx)
        except Exception as e:
            logger.error(f"Erro ao extrair texto do docx: {e}")
            raise HTTPException(status_code=400, detail=f"Erro ao extrair texto do docx: {str(e)}")
        blob_folder = f"{usuario_executor}/{nome_projeto}/arquivos_recebidos/docx"
        blob_filename = f"{analysis_type}.docx"
        blob_url = await upload_docx_to_blob(
            arquivo_docx,
            blob_folder,
            blob_filename,
            background_tasks
        )
    if not texto_extraido and not comentario_extra:
        raise HTTPException(status_code=400, detail="É obrigatório fornecer arquivo_docx ou comentario_extra.")
    session_exists = bool(project_state)
    if session_exists:
        redis_service.restore_session_from_state(
            usuario_executor,
            nome_projeto,
            analysis_type,
            project_state
        )
    else:
        redis_service.create_session(
            usuario_executor,
            nome_projeto,
            analysis_type,
            project_id=project_id_final,
            extracted_text=texto_extraido
        )
    if blob_url:
        redis_service.add_docx_file(project_id_final, blob_url)
    mcp_payload = {
        "project_id": project_id_final,
        "texto_extraido_do_docx": texto_extraido,
        "comentario_extra": comentario_extra,
        "analysis_type": analysis_type
    }
    mcp_client = MCPClientService()
    try:
        await mcp_client.start_analysis(mcp_payload)
    except Exception as e:
        logger.error(f"Erro na comunicação com MCP: {e}")
        raise HTTPException(status_code=502, detail=f"Erro ao comunicar com o servidor de Inteligência (MCP): {str(e)}")
    return StartAnalysisResponse(
        message="Análise solicitada com sucesso ao agente.",
        project_id=project_id_final,
        nome_projeto=nome_projeto
    )
