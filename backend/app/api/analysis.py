import logging
from fastapi import APIRouter, HTTPException, Depends, Body, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from ..middleware.auth_middleware import get_current_user, _extract_usuario_executor
from ..services.mcp_client_service import MCPClientService, MCPStartAnalysisPayload
from ..services.redis_session_service import RedisSessionService
from ..services.project_state_service import ProjectStateService
from ..services.background_state_saver import BackgroundStateSaver

import uuid

router = APIRouter()
logger = logging.getLogger("analysis_api")

class StartAnalysisRequest(BaseModel):
    projeto: str
    analysis_type: str
    comentario_usuario: Optional[str] = None
    arquivo_docx: Optional[str] = None
    project_id: Optional[str] = None

class StartAnalysisResponse(BaseModel):
    message: str
    project_id: str

@router.post("/start", response_model=StartAnalysisResponse, tags=["Analysis"])
async def start_analysis(
    background_tasks: BackgroundTasks,
    projeto: str = Body(...),
    analysis_type: str = Body(...),
    comentario_usuario: Optional[str] = Body(None),
    arquivo_docx: Optional[str] = Body(None),
    project_id: Optional[str] = Body(None),
    current_user: dict = Depends(get_current_user)
):
    usuario_executor = _extract_usuario_executor(current_user)
    logger.info(f"Iniciando análise para projeto '{projeto}' (analysis_type: '{analysis_type}') para usuário {usuario_executor}")
    redis_service = RedisSessionService()
    project_id_final = project_id
    if not project_id_final:
        project_id_final = await ProjectStateService._get_project_id_by_name(usuario_executor, projeto)
    if not project_id_final:
        project_id_final = str(uuid.uuid4())
    project_state = None
    if project_id_final:
        project_state = await ProjectStateService.load_latest_state_from_blob(usuario_executor, project_id=project_id_final)
    session_exists = bool(project_state)
    texto_extraido = None
    if arquivo_docx is not None:
        texto_extraido = arquivo_docx
    else:
        if session_exists:
            try:
                session = redis_service.get_session_by_project_id(project_id_final)
                texto_extraido = getattr(session, "extracted_text", None)
            except Exception as e:
                logger.error(f"Erro ao buscar texto extraído da sessão: {e}")
                texto_extraido = None
    if session_exists:
        redis_service.restore_session_from_state(
            usuario_executor,
            projeto,
            analysis_type,
            project_state
        )
    else:
        redis_service.create_session(
            usuario_executor,
            projeto,
            analysis_type,
            project_id=project_id_final,
            comentario_usuario=comentario_usuario,
            extracted_text=texto_extraido
        )
    BackgroundStateSaver.schedule_periodic_save(project_id_final)
    mcp_payload = MCPStartAnalysisPayload(
        projeto=projeto,
        analysis_type=analysis_type,
        arquivo_docx=texto_extraido,
        comentario_usuario=comentario_usuario,
        usuario_executor=usuario_executor,
        project_id=project_id_final
    )
    mcp_client = MCPClientService()
    try:
        await mcp_client.start_analysis(mcp_payload)
    except Exception as e:
        logger.error(f"Erro na comunicação com MCP: {e}")
        raise HTTPException(status_code=502, detail=f"Erro ao comunicar com o servidor de Inteligência (MCP): {str(e)}")
    return StartAnalysisResponse(
        message="Análise solicitada com sucesso ao agente.",
        project_id=project_id_final
    )
