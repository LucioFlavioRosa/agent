import os
import uuid
import logging

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from backend.app.services.mcp_client_service import MCPClientService
from backend.app.services.mcp_config_service import MCPConfigService
from backend.app.services.permission_service import PermissionService
from backend.app.services.mongodb_service import MongoDBService
from backend.app.utils.string_utils import normalize_string_general
from backend.app.utils.logging_utils import (
    log_request_received,
    log_validation_step,
    log_service_call,
    log_response_sent,
    log_error
)

router = APIRouter()
logger = logging.getLogger("analysis_api")

# Configuração de segurança para arquivos
ALLOWED_EXTENSIONS = {".docx"}

class StartAnalysisRequest(BaseModel):
    email: Optional[str] = None
    nome_projeto: Optional[str] = None
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
        log_validation_step(
            step="validate_file_extension",
            status="fail",
            details=f"Extensão de arquivo '{extension}' não permitida.",
            job_id=None,
            project_id=None
        )
        logger.warning(f"Tentativa de upload de arquivo inválido: {file.filename}")
        raise HTTPException(
            status_code=400, 
            detail=f"Extensão de arquivo '{extension}' não permitida. Use apenas: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    log_validation_step(
        step="validate_file_extension",
        status="success",
        details=f"Arquivo '{file.filename}' validado com extensão '{extension}'.",
        job_id=None,
        project_id=None
    )

async def validate_user_and_company(email: Optional[str], mongo_service: MongoDBService):
    if not email:
        log_validation_step(
            step="validate_user_and_company",
            status="fail",
            details="Campo 'email' do usuário é obrigatório.",
            job_id=None,
            project_id=None
        )
        raise HTTPException(status_code=400, detail="Campo 'email' do usuário é obrigatório.")
    user = await mongo_service.get_user_by_email(email)
    if not user:
        log_validation_step(
            step="validate_user_and_company",
            status="fail",
            details="Usuário não encontrado.",
            job_id=None,
            project_id=None
        )
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    company_id = getattr(user, "company_id", None)
    if not company_id:
        log_validation_step(
            step="validate_user_and_company",
            status="fail",
            details="Usuário não possui company_id.",
            job_id=None,
            project_id=None
        )
        raise HTTPException(status_code=400, detail="Usuário não possui company_id.")
    log_validation_step(
        step="validate_user_and_company",
        status="success",
        details="Usuário e company_id validados.",
        job_id=None,
        project_id=None
    )
    return user, company_id

async def get_or_create_project(nome_projeto: Optional[str], analysis_type: Optional[str], email: str, user, company_id, mongo_service: MongoDBService):
    if not nome_projeto or not analysis_type:
        log_validation_step(
            step="get_or_create_project",
            status="fail",
            details="Campos obrigatórios ausentes: nome_projeto, analysis_type.",
            job_id=None,
            project_id=None
        )
        raise HTTPException(status_code=400, detail="Campos obrigatórios ausentes: nome_projeto, analysis_type.")
    
    nome_projeto_normalized = normalize_string_general(nome_projeto)
    project = await mongo_service.get_project_by_normalized_name(nome_projeto_normalized, company_id)
    
    if not project:
        permission_service = PermissionService(mongo_service)

        can_create, error_msg_create = await permission_service.check_user_can_create_project(email, company_id)
        if not can_create:
            log_validation_step(
                step="get_or_create_project",
                status="fail",
                details=error_msg_create,
                job_id=None,
                project_id=None
            )
            raise HTTPException(status_code=403, detail=error_msg_create)
            
        has_access, error_msg = await permission_service.check_user_agent_permission(email, analysis_type)
        if not has_access:
            log_validation_step(
                step="get_or_create_project",
                status="fail",
                details=error_msg or "Usuário não possui permissão para usar este agente.",
                job_id=None,
                project_id=None
            )
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
        created = await mongo_service.create_project(project_data, company_id)
        if not created:
            log_error(
                context="get_or_create_project",
                error_message=f"Falha ao criar projeto {nome_projeto} para usuário {email}",
                exception=None,
                job_id=None,
                project_id=project_id
            )
            logger.error(f"Falha ao criar projeto {nome_projeto} para usuário {email}")
            raise HTTPException(status_code=500, detail="Falha ao criar projeto no MongoDB.")
        log_validation_step(
            step="get_or_create_project",
            status="success",
            details=f"Projeto criado: {project_id}",
            job_id=None,
            project_id=project_id
        )
    else:
        project_id = getattr(project, "id", None) or project.get("_id")
        log_validation_step(
            step="get_or_create_project",
            status="success",
            details=f"Projeto encontrado: {project_id}",
            job_id=None,
            project_id=project_id
        )
    
    return project_id, nome_projeto

@router.post("/start", response_model=StartAnalysisResponse, tags=["Analysis"])
async def start_analysis(
    email: Optional[str] = Form(None),
    nome_projeto: Optional[str] = Form(None),
    analysis_type: Optional[str] = Form(None),
    branch: Optional[str] = Form(None),
    repository: Optional[str] = Form(None),
    comentario_extra: Optional[str] = Form(None),
    arquivo_docx: Optional[UploadFile] = File(None),
    mongo_service: MongoDBService = Depends(lambda request: request.app.state.mongo_service)
):
    # 1. Log recebimento do payload
    payload = {
        "email": email,
        "nome_projeto": nome_projeto,
        "analysis_type": analysis_type,
        "branch": branch,
        "repository": repository,
        "comentario_extra": comentario_extra,
        "arquivo_docx": arquivo_docx.filename if arquivo_docx else None
    }
    log_request_received(endpoint="/analysis/start", payload=payload)

    # 2. Validação de Segurança do Arquivo
    if arquivo_docx:
        validate_file_extension(arquivo_docx)

    logger.info(f"Iniciando análise multiagente para projeto '{nome_projeto}' para usuário {email}")
    
    # 3. Validação de usuário e company_id
    user, company_id = await validate_user_and_company(email, mongo_service)
    
    # 4. Criação ou busca de projeto
    project_id, nome_projeto_final = await get_or_create_project(
        nome_projeto, analysis_type, email, user, company_id, mongo_service
    )

    # 5. Verifica permissão do usuário para executar ação no projeto
    try:
        permission_service = PermissionService(mongo_service)
        has_permission, member_role, error_msg = await permission_service.check_user_project_action_permission(
            email, project_id, action_type="edit_project"
        )
        log_validation_step(
            step="check_user_project_action_permission",
            status="success" if has_permission else "fail",
            details="Permissão validada para ação de edição no projeto." if has_permission else (error_msg or "Usuário não possui permissão para executar esta ação no projeto."),
            job_id=None,
            project_id=project_id
        )
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail=error_msg or "Usuário não possui permissão para executar esta ação no projeto."
            )
    except HTTPException as exc:
        log_error(
            context="check_user_project_action_permission",
            error_message=str(exc.detail),
            exception=exc,
            job_id=None,
            project_id=project_id
        )
        raise
    except Exception as e:
        log_error(
            context="check_user_project_action_permission",
            error_message="Erro ao validar permissões de ação do usuário.",
            exception=e,
            job_id=None,
            project_id=project_id
        )
        logger.error(f"Erro ao validar permissões de ação: {e}")
        raise HTTPException(status_code=500, detail="Erro ao validar permissões do usuário.")

    # 6. Busca configuração do agente via MCPConfigService
    agent_cfg = MCPConfigService.get_agent_config(analysis_type)
    if not agent_cfg or not agent_cfg.mcp_service_url:
        log_error(
            context="get_agent_config",
            error_message=f"Configuração do agente '{analysis_type}' inválida ou URL do MCP ausente.",
            exception=None,
            job_id=None,
            project_id=project_id
        )
        logger.error(f"Configuração do agente '{analysis_type}' inválida ou URL do MCP ausente.")
        raise HTTPException(status_code=500, detail=f"Configuração do agente '{analysis_type}' não disponível.")
    log_validation_step(
        step="get_agent_config",
        status="success",
        details=f"Configuração do agente '{analysis_type}' carregada.",
        job_id=None,
        project_id=project_id
    )

    # 7. Gera job_id único para rastreamento da execução
    job_id = str(uuid.uuid4())
    log_validation_step(
        step="generate_job_id",
        status="success",
        details=f"job_id gerado: {job_id}",
        job_id=job_id,
        project_id=project_id
    )

    # 8. Monta payload para o serviço MCP
    mcp_payload = {
        "email": email,
        "nome_projeto": nome_projeto_final,
        "analysis_type": analysis_type,
        "branch": branch,
        "repository": repository,
        "comentario_extra": comentario_extra,
        "project_id": project_id,
        "job_id": job_id,
        "company_id": company_id
    }
    log_service_call(
        service="MCPClientService",
        action="build_payload",
        payload=mcp_payload,
        job_id=job_id,
        project_id=project_id
    )

    # 9. Comunicação com o serviço MCP via Client Service
    mcp_client = MCPClientService(base_url=agent_cfg.mcp_service_url)
    try:
        log_service_call(
            service="MCPClientService",
            action="start_analysis_call",
            payload=mcp_payload,
            job_id=job_id,
            project_id=project_id
        )
        await mcp_client.start_analysis(mcp_payload, agent_cfg.mcp_service_url, arquivo_docx)
        log_service_call(
            service="MCPClientService",
            action="start_analysis_success",
            response="Solicitação enviada com sucesso ao MCP.",
            job_id=job_id,
            project_id=project_id
        )
    except Exception as e:
        log_error(
            context="MCPClientService.start_analysis",
            error_message=f"Erro na comunicação com MCP para o job {job_id}: {str(e)}",
            exception=e,
            job_id=job_id,
            project_id=project_id
        )
        logger.error(f"Erro na comunicação com MCP para o job {job_id}: {e}")
        raise HTTPException(status_code=502, detail=f"O serviço de agentes (MCP) retornou um erro: {str(e)}")

    response_obj = StartAnalysisResponse(
        message="Análise multiagente solicitada com sucesso ao MCP.",
        project_id=project_id,
        job_id=job_id,
        nome_projeto=nome_projeto_final
    )
    log_response_sent(endpoint="/analysis/start", response=response_obj.dict(), job_id=job_id, project_id=project_id)
    return response_obj
