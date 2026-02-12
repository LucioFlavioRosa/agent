import logging
import uuid
import os
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from backend.app.services.mcp_client_service import MCPClientService
from backend.app.services.mcp_config_service import MCPConfigService
from backend.app.services.permission_service import PermissionService
from backend.app.services.mongodb_service import MongoDBService

router = APIRouter()
logger = logging.getLogger("analysis_api")

# Configuração de segurança para arquivos
ALLOWED_EXTENSIONS = {".docx"}

class StartAnalysisRequest(BaseModel):
    email: Optional[str] = None
    nome_projeto: Optional[str] = None
    agent_name: Optional[str] = None
    analysis_type: Optional[str] = None
    branch: Optional[str] = None
    repository: Optional[str] = None
    comentario_extra: Optional[str] = None

class StartAnalysisResponse(BaseModel):
    message: str
    project_id: Optional[str] = None
    job_id: Optional[str] = None
    nome_projeto: Optional[str] = None

def validate_file_extension(file: UploadFile):
    """Valida se o arquivo enviado possui uma extensão permitida."""
    extension = os.path.splitext(file.filename)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        logger.warning(f"Tentativa de upload de arquivo inválido: {file.filename}")
        raise HTTPException(
            status_code=400, 
            detail=f"Extensão de arquivo '{extension}' não permitida. Use apenas: {', '.join(ALLOWED_EXTENSIONS)}"
        )

async def validate_user_and_company(email: Optional[str], mongo_service: MongoDBService):
    if not email:
        raise HTTPException(status_code=400, detail="Campo 'email' do usuário é obrigatório.")
    user = await mongo_service.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    company_id = getattr(user, "company_id", None)
    if not company_id:
        raise HTTPException(status_code=400, detail="Usuário não possui company_id.")
    return user, company_id

async def get_or_create_project(nome_projeto: Optional[str], agent_name: Optional[str], email: str, user, company_id, mongo_service: MongoDBService):
    if not nome_projeto or not agent_name:
        raise HTTPException(status_code=400, detail="Campos obrigatórios ausentes: nome_projeto, agent_name.")
    
    def normalize_project_name(name):
        return name.strip().lower().replace(" ", "_")
    
    nome_projeto_normalized = normalize_project_name(nome_projeto)
    project = await mongo_service.get_project_by_normalized_name(nome_projeto_normalized, company_id)
    
    if not project:
        permission_service = PermissionService(mongo_service)
        has_access, error_msg = await permission_service.check_user_agent_permission(email, agent_name)
        if not has_access:
            raise HTTPException(status_code=403, detail=error_msg or "Usuário não possui permissão para usar este agente.")
        
        project_id = str(uuid.uuid4())
        project_data = {
            "_id": project_id,
            "name": nome_projeto,
            "name_normalized": nome_projeto_normalized,
            "company_id": company_id,
            "members": [
                {
                    "user_id": user.id,
                    "email": email,
                    "role": "owner",
                    "added_at": datetime.utcnow().isoformat()
                }
            ],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "description": None
        }
        created = await mongo_service.create_project(project_data)
        if not created:
            logger.error(f"Falha ao criar projeto {nome_projeto} para usuário {email}")
            raise HTTPException(status_code=500, detail="Falha ao criar projeto no MongoDB.")
    else:
        project_id = getattr(project, "id", None) or project.get("_id")
    
    return project_id, nome_projeto

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
    # 1. Validação de Segurança do Arquivo
    if arquivo_docx:
        validate_file_extension(arquivo_docx)

    logger.info(f"Iniciando análise multiagente para projeto '{nome_projeto}' para usuário {email}")

    mongo_service = MongoDBService()
    
    # 2. Validação de usuário e company_id
    user, company_id = await validate_user_and_company(email, mongo_service)
    
    # 3. Criação ou busca de projeto
    project_id, nome_projeto_final = await get_or_create_project(
        nome_projeto, agent_name, email, user, company_id, mongo_service
    )

    # 4. Verifica permissão do usuário para executar ação no projeto
    try:
        permission_result = await PermissionService(mongo_service).check_user_project_permission(
            email, project_id, agent_name, "write"
        )
        if not permission_result[0]:
            raise HTTPException(
                status_code=403, 
                detail=permission_result[2] or "Usuário não possui permissão para executar esta ação no projeto."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao validar permissões: {e}")
        raise HTTPException(status_code=500, detail="Erro ao validar permissões do usuário.")

    # 5. Busca configuração do agente via MCPConfigService
    agent_cfg = MCPConfigService.get_agent_config(agent_name)
    if not agent_cfg or not agent_cfg.mcp_service_url:
        logger.error(f"Configuração do agente '{agent_name}' inválida ou URL do MCP ausente.")
        raise HTTPException(status_code=500, detail=f"Configuração do agente '{agent_name}' não disponível.")

    # 6. Gera job_id único para rastreamento da execução
    job_id = str(uuid.uuid4())

    # 7. Monta payload para o serviço MCP
    mcp_payload = {
        "email": email,
        "nome_projeto": nome_projeto_final,
        "agent_name": agent_name,
        "analysis_type": analysis_type,
        "branch": branch,
        "repository": repository,
        "comentario_extra": comentario_extra,
        "project_id": project_id,
        "job_id": job_id
    }

    # 8. Comunicação com o serviço MCP via Client Service
    mcp_client = MCPClientService(base_url=agent_cfg.mcp_service_url)
    try:
        # Nota: O arquivo_docx é passado separadamente para ser tratado como multipart
        await mcp_client.start_analysis(mcp_payload, agent_cfg.mcp_service_url, arquivo_docx)
    except Exception as e:
        logger.error(f"Erro na comunicação com MCP para o job {job_id}: {e}")
        raise HTTPException(status_code=502, detail=f"O serviço de agentes (MCP) retornou um erro: {str(e)}")

    return StartAnalysisResponse(
        message="Análise multiagente solicitada com sucesso ao MCP.",
        project_id=project_id,
        job_id=job_id,
        nome_projeto=nome_projeto_final
    )
