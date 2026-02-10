import logging
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional

from backend.app.services.mcp_client_service import MCPClientService
from backend.app.services.mcp_config_service import MCPConfigService
from backend.app.services.permission_service import PermissionService

router = APIRouter()
logger = logging.getLogger("analysis_api")

class StartAnalysisRequest(BaseModel):
    email: Optional[str] = None
    nome_projeto: Optional[str] = None
    agent_name: Optional[str] = None
    analysis_type: Optional[str] = None
    branch: Optional[str] = None
    repository: Optional[str] = None
    comentario_extra: Optional[str] = None
    # arquivo_docx será tratado separadamente

class StartAnalysisResponse(BaseModel):
    message: str
    project_id: Optional[str] = None
    job_id: Optional[str] = None
    nome_projeto: Optional[str] = None

@router.post("/start", response_model=StartAnalysisResponse, tags=["Analysis"])
async def start_analysis(
    email: Optional[str] = Form(None),
    nome_projeto: Optional[str] = Form(None),
    agent_name: Optional[str] = Form(None),
    analysis_type: Optional[str] = Form(None),
    branch: Optional[str] = Form(None),
    repository: Optional[str] = Form(None),
    comentario_extra: Optional[str] = Form(None),
    arquivo_docx: Optional[UploadFile] = File(None)
):
    logger.info(f"Iniciando análise multiagente para projeto '{nome_projeto}' (agent_name: '{agent_name}', analysis_type: '{analysis_type}') para usuário {email}")

    # Validação mínima dos campos obrigatórios
    if not nome_projeto or not agent_name:
        raise HTTPException(status_code=400, detail="Campos obrigatórios ausentes: nome_projeto, agent_name.")
    if not email:
        raise HTTPException(status_code=400, detail="Campo 'email' do usuário é obrigatório.")

    # 1. Verifica permissão do usuário para executar ação no projeto
    try:
        permission_result = await PermissionService.check_user_project_permission(email, nome_projeto, agent_name)
        if not permission_result["authorized"]:
            raise HTTPException(status_code=403, detail="Usuário não possui permissão para executar esta ação no projeto.")
        project_id = permission_result["project_id"]
    except Exception as e:
        logger.error(f"Erro ao validar permissões: {e}")
        raise HTTPException(status_code=500, detail="Erro ao validar permissões do usuário.")

    # 2. Busca configuração do agente via MCPConfigService
    agent_cfg = MCPConfigService.get_agent_config(agent_name)
    if not agent_cfg:
        logger.error(f"Configuração do agente '{agent_name}' não encontrada.")
        raise HTTPException(status_code=400, detail=f"Configuração do agente '{agent_name}' não encontrada.")
    mcp_service_url = agent_cfg.mcp_service_url
    if not mcp_service_url:
        raise HTTPException(status_code=500, detail=f"URL do MCP Service não configurada para agente '{agent_name}'.")

    # 3. Gera job_id único
    job_id = str(uuid.uuid4())

    # 4. Monta payload para MCP
    mcp_payload = {
        "email": email,
        "nome_projeto": nome_projeto,
        "agent_name": agent_name,
        "analysis_type": analysis_type,
        "branch": branch,
        "repository": repository,
        "comentario_extra": comentario_extra,
        "project_id": project_id,
        "job_id": job_id
    }

    mcp_client = MCPClientService(base_url=mcp_service_url)
    try:
        mcp_response = await mcp_client.start_analysis(mcp_payload, mcp_service_url, arquivo_docx)
    except Exception as e:
        logger.error(f"Erro na comunicação com MCP: {e}")
        raise HTTPException(status_code=502, detail=f"Erro ao comunicar com o MCP Service: {str(e)}")

    return StartAnalysisResponse(
        message="Análise multiagente solicitada com sucesso ao MCP.",
        project_id=project_id,
        job_id=job_id,
        nome_projeto=nome_projeto
    )
