import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Form, BackgroundTasks, UploadFile, File, Request
from pydantic import BaseModel

from ..middleware.auth_middleware import get_current_user, _extract_usuario_executor
from ..services.mcp_client_service import MCPClientService
from ..services.redis_session_service import RedisSessionService

router = APIRouter()
logger = logging.getLogger("analysis_api")

class StartAnalysisResponse(BaseModel):
    message: str
    project_id: str
    job_id: str
    nome_projeto: Optional[str] = None

# Cache simples para project_id por usuario_executor e nome_projeto
_project_id_cache = {}

def _get_or_create_project_id(usuario_executor: str, nome_projeto: str) -> str:
    key = f"{usuario_executor}:{nome_projeto.strip().lower()}"
    if key in _project_id_cache:
        return _project_id_cache[key]
    project_id = str(uuid.uuid4())
    _project_id_cache[key] = project_id
    return project_id

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

    if not usuario_executor or not isinstance(usuario_executor, str) or not usuario_executor.strip():
        logger.error(f"Falha ao extrair usuario_executor do token JWT: '{usuario_executor}'")
        raise HTTPException(status_code=401, detail="Campo 'usuario_executor' ausente ou inválido no token JWT.")

    if not nome_projeto or not isinstance(nome_projeto, str) or not nome_projeto.strip():
        logger.error(f"Campo 'nome_projeto' ausente ou vazio no formulário: '{nome_projeto}'")
        raise HTTPException(status_code=400, detail="Campo 'nome_projeto' ausente ou vazio no formulário.")

    if not analysis_type or not isinstance(analysis_type, str) or not analysis_type.strip():
        logger.error(f"Campo 'analysis_type' ausente ou vazio no formulário: '{analysis_type}'")
        raise HTTPException(status_code=400, detail="Campo 'analysis_type' ausente ou vazio no formulário.")

    # Gerar ou recuperar project_id
    project_id = _get_or_create_project_id(usuario_executor, nome_projeto)

    # Criar job no Redis
    redis_service = RedisSessionService()
    job_id = redis_service.create_job(project_id, analysis_type)

    # Montar payload para MCP
    mcp_payload = {
        "project_id": project_id,
        "analysis_type": analysis_type,
        "job_id": job_id,
        "nome_projeto": nome_projeto,
        "usuario_executor": usuario_executor,
        "comentario_extra": comentario_extra
    }

    mcp_client = MCPClientService()
    try:
        await mcp_client.start_analysis(mcp_payload, arquivo_docx=arquivo_docx)
    except Exception as e:
        logger.error(f"Erro na comunicação com MCP: {e}")
        raise HTTPException(status_code=502, detail=f"Erro ao comunicar com o servidor de Inteligência (MCP): {str(e)}")

    return StartAnalysisResponse(
        message="Análise solicitada com sucesso ao agente.",
        project_id=project_id,
        job_id=job_id,
        nome_projeto=nome_projeto
    )
