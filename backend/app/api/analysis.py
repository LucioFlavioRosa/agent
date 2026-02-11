import logging
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel
from typing import Optional

from backend.app.services.mcp_client_service import MCPClientService
from backend.app.services.mcp_config_service import MCPConfigService
from backend.app.services.permission_service import PermissionService
from backend.app.services.mongodb_service import MongoDBService

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

async def get_mongo_service():
    from backend.app.core.config import settings
    mongo_uri = getattr(settings, "MONGODB_URI", None)
    mongo_db_name = getattr(settings, "MONGODB_DATABASE_NAME", None)
    return MongoDBService(uri=mongo_uri, db_name=mongo_db_name)

@router.post("/start", response_model=StartAnalysisResponse, tags=["Analysis"])
async def start_analysis(
    email: Optional[str] = Form(None),
    nome_projeto: Optional[str] = Form(None),
    agent_name: Optional[str] = Form(None),
    analysis_type: Optional[str] = Form(None),
    branch: Optional[str] = Form(None),
    repository: Optional[str] = Form(None),
    comentario_extra: Optional[str] = Form(None),
    arquivo_docx: Optional[UploadFile] = File(None),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    logger.info(f"Iniciando análise multiagente para projeto '{nome_projeto}' (agent_name: '{agent_name}', analysis_type: '{analysis_type}') para usuário {email}")

    # Validação mínima dos campos obrigatórios
    if not nome_projeto or not agent_name:
        raise HTTPException(status_code=400, detail="Campos obrigatórios ausentes: nome_projeto, agent_name.")
    if not email:
        raise HTTPException(status_code=400, detail="Campo 'email' do usuário é obrigatório.")

    permission_service = PermissionService(mongo_service)

    # 1. Verifica se projeto existe pelo nome
    project_doc = None
    project_id = None
    # Busca projeto por nome
    project_cursor = mongo_service.db.projects.find({"name": nome_projeto})
    project_list = [doc async for doc in project_cursor]
    if project_list:
        project_doc = project_list[0]
        project_id = str(project_doc.get("_id"))
    else:
        project_doc = None

    if not project_doc:
        # Projeto não existe: verifica acesso ao agente
        has_access, access_msg = await permission_service.check_user_agent_access(email, agent_name)
        if not has_access:
            raise HTTPException(status_code=403, detail=access_msg)
        # Cria novo projeto
        project_id = str(uuid.uuid4())
        user = await mongo_service.get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=400, detail="Usuário não encontrado.")
        user_id = user.id
        company_id = user.company_id
        # Criação do projeto
        result = await mongo_service.create_project(
            project_id=project_id,
            nome_projeto=nome_projeto,
            company_id=company_id,
            email=email,
            user_id=user_id
        )
        if not result:
            raise HTTPException(status_code=500, detail="Erro ao criar projeto no MongoDB.")
    else:
        # Projeto já existe: verifica permissão
        has_perm, member_role, perm_msg = await permission_service.check_user_project_permission(
            email=email,
            project_id=project_id,
            agent_name=agent_name,
            action_type="write"
        )
        if not has_perm:
            raise HTTPException(status_code=403, detail=perm_msg or "Usuário não possui permissão para executar esta ação no projeto.")

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
