import logging
from fastapi import APIRouter, HTTPException, Depends, Body, BackgroundTasks, UploadFile, File
from pydantic import BaseModel, root_validator
from typing import Optional

from ..middleware.auth_middleware import get_current_user
from ..services.mcp_client_service import MCPClientService, MCPStartAnalysisPayload
from ..services.redis_session_service import RedisSessionService
from ..services.project_state_service import ProjectStateService
from ..services.background_state_saver import BackgroundStateSaver
from ..services.docx_parser_service import extract_text_from_docx

router = APIRouter()
logger = logging.getLogger("analysis_api")

class StartAnalysisRequest(BaseModel):
    projeto: str
    analysis_type: str
    comentario_usuario: Optional[str] = None

class StartAnalysisResponse(BaseModel):
    job_id: str
    message: str
    session_id: str

@router.post("/start", response_model=StartAnalysisResponse, tags=["Analysis"])
async def start_analysis(
    background_tasks: BackgroundTasks,
    projeto: str = Body(...),
    analysis_type: str = Body(...),
    arquivo_docx: Optional[UploadFile] = File(None),
    comentario_usuario: Optional[str] = Body(None),
    current_user: dict = Depends(get_current_user)
):
    usuario_executor = current_user.get("usuario_executor") or current_user.get("sub")
    logger.info(f"Iniciando análise para projeto '{projeto}' (analysis_type: '{analysis_type}') para usuário {usuario_executor}")
    redis_service = RedisSessionService()
    session_id = None
    texto_extraido = None
    if arquivo_docx is not None:
        try:
            texto_extraido = await extract_text_from_docx(arquivo_docx)
            await arquivo_docx.seek(0)
        except Exception as e:
            logger.error(f"Erro ao extrair texto do arquivo DOCX: {e}")
            raise HTTPException(status_code=400, detail=f"Erro ao processar o arquivo DOCX: {str(e)}")
    # Criação ou restauração de sessão
    project_state = await ProjectStateService.load_latest_state_from_blob(usuario_executor, projeto)
    if project_state:
        session_id = redis_service.restore_session_from_state(
            usuario_executor,
            projeto,
            analysis_type,
            project_state
        )
        if arquivo_docx is not None:
            try:
                redis_service.add_docx_file(session_id, f"arquivo_docx_{session_id}")
            except Exception as e:
                logger.error(f"Erro ao adicionar arquivo DOCX à sessão durante análise: {e}")
    else:
        session_id = redis_service.create_session(
            usuario_executor,
            projeto,
            analysis_type,
            comentario_usuario=comentario_usuario
        )
        if arquivo_docx is not None:
            try:
                redis_service.add_docx_file(session_id, f"arquivo_docx_{session_id}")
            except Exception as e:
                logger.error(f"Erro ao adicionar arquivo DOCX à sessão recém-criada: {e}")
    BackgroundStateSaver.schedule_periodic_save(session_id)
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
