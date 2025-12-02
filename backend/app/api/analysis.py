import logging
from fastapi import APIRouter, HTTPException, Depends, Body, BackgroundTasks
from pydantic import BaseModel
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
    analysis_name: str
    analysis_type: str
    extracted_text: Optional[str] = None
    blob_url: Optional[str] = None
    session_id: Optional[str] = None

class StartAnalysisResponse(BaseModel):
    job_id: str
    message: str
    session_id: str

@router.post("/start", response_model=StartAnalysisResponse, tags=["Analysis"])
async def start_analysis(
    payload_request: StartAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    usuario_executor = current_user.get("usuario_executor") or current_user.get("sub")
    logger.info(f"Iniciando análise '{payload_request.analysis_name}' do tipo '{payload_request.analysis_type}' para usuário {usuario_executor}")
    redis_service = RedisSessionService()
    session_id = payload_request.session_id
    project_state = await ProjectStateService.load_latest_state_from_blob(usuario_executor, payload_request.projeto)
    if project_state:
        session_id = redis_service.restore_session_from_state(
            usuario_executor,
            payload_request.projeto,
            payload_request.analysis_name,
            payload_request.analysis_type,
            project_state
        )
        instrucoes_extras = payload_request.extracted_text if payload_request.extracted_text is not None else ""
    else:
        if not payload_request.extracted_text:
            logger.error("Para criar um novo projeto, o campo 'extracted_text' (texto extraído do DOCX) é obrigatório.")
            raise HTTPException(status_code=400, detail="O upload do DOCX é obrigatório para novos projetos.")
        session_id = redis_service.create_session(
            usuario_executor,
            payload_request.projeto,
            payload_request.analysis_name,
            payload_request.analysis_type
        )
        instrucoes_extras = payload_request.extracted_text
        if payload_request.blob_url:
            try:
                redis_service.add_docx_file(session_id, payload_request.blob_url)
            except Exception as e:
                logger.error(f"Erro ao adicionar arquivo DOCX à sessão durante análise: {e}")
    BackgroundStateSaver.schedule_periodic_save(session_id)
    mcp_payload = MCPStartAnalysisPayload(
        analysis_type=payload_request.analysis_type,
        instrucoes_extras=instrucoes_extras,
        projeto=payload_request.projeto,
        analysis_name=payload_request.analysis_name,
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
