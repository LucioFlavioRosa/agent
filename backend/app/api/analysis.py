import logging
from fastapi import APIRouter, HTTPException, Depends, Body, BackgroundTasks, UploadFile, File
from pydantic import BaseModel, root_validator
from typing import Optional

from ..middleware.auth_middleware import get_current_user
from ..services.mcp_client_service import MCPClientService, MCPStartAnalysisPayload
from ..services.redis_session_service import RedisSessionService
from ..services.project_state_service import ProjectStateService
from ..services.background_state_saver import BackgroundStateSaver

router = APIRouter()
logger = logging.getLogger("analysis_api")

class StartAnalysisRequest(BaseModel):
    projeto: str
    analysis_type: str
    comentario_usuario: Optional[str] = None
    arquivo_docx: Optional[str] = None  # Agora é texto extraído

class StartAnalysisResponse(BaseModel):
    job_id: str
    message: str
    session_id: str

@router.post("/start", response_model=StartAnalysisResponse, tags=["Analysis"])
async def start_analysis(
    background_tasks: BackgroundTasks,
    projeto: str = Body(...),
    analysis_type: str = Body(...),
    comentario_usuario: Optional[str] = Body(None),
    arquivo_docx: Optional[str] = Body(None),  # Texto extraído
    current_user: dict = Depends(get_current_user)
):
    usuario_executor = current_user.get("usuario_executor") or current_user.get("sub")
    logger.info(f"Iniciando análise para projeto '{projeto}' (analysis_type: '{analysis_type}') para usuário {usuario_executor}")
    redis_service = RedisSessionService()
    session_id = None
    texto_extraido = None
    # Criação ou restauração de sessão
    project_state = await ProjectStateService.load_latest_state_from_blob(usuario_executor, projeto)
    if project_state:
        session_id = redis_service.restore_session_from_state(
            usuario_executor,
            projeto,
            analysis_type,
            project_state
        )
    else:
        session_id = redis_service.create_session(
            usuario_executor,
            projeto,
            analysis_type,
            comentario_usuario=comentario_usuario
        )
    BackgroundStateSaver.schedule_periodic_save(session_id)
    # Busca o texto extraído da sessão Redis, a menos que seja enviado diretamente
    if arquivo_docx is not None:
        texto_extraido = arquivo_docx
    else:
        try:
            session = redis_service.get_session(session_id)
            texto_extraido = getattr(session, "extracted_text", None)
        except Exception as e:
            logger.error(f"Erro ao buscar texto extraído da sessão: {e}")
            texto_extraido = None
    mcp_payload = MCPStartAnalysisPayload(
        projeto=projeto,
        analysis_type=analysis_type,
        arquivo_docx=texto_extraido,
        comentario_usuario=comentario_usuario,
        usuario_executor=usuario_executor,
        session_id=session_id
    )
    mcp_client = MCPClientService()
    try:
        mcp_response = await mcp_client.start_analysis(mcp_payload)
        job_id = mcp_response.job_id
    except Exception as e:
        logger.error(f"Erro na comunicação com MCP: {e}")
        raise HTTPException(status_code=502, detail=f"Erro ao comunicar com o servidor de Inteligência (MCP): {str(e)}")
    return StartAnalysisResponse(
        job_id=job_id,
        message="Análise solicitada com sucesso ao agente.",
        session_id=session_id
    )
