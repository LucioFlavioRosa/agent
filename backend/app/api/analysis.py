import os
import uuid
import logging

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from backend.app.services.mcp_client_service import MCPClientService
from backend.app.services.mcp_config_service import MCPConfigService
from backend.app.services.permission_service import PermissionService
from backend.app.services.mongodb_service import MongoDBService
from backend.app.utils.string_utils import normalize_string_general
from backend.app.services.redis_session_service import RedisSessionService
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

CATEGORY_DEPENDENCIES = {
    "epics": [],
    "features": ["epics"],
    "timeline": ["epics", "features"],
    "risks": ["epics", "features", "timeline"]
}

class StartAnalysisRequest(BaseModel):
    email: Optional[str] = None
    nome_projeto: Optional[str] = None
    category: Optional[str] = None # Ex: "epics", "features"
    action: Optional[str] = None   # Ex: "generator", "reviwer"
    branch: Optional[str] = None
    repository: Optional[str] = None
    comentario_extra: Optional[str] = None

class StartAnalysisResponse(BaseModel):
    message: str
    project_id: Optional[str] = None
    job_id: Optional[str] = None
    nome_projeto: Optional[str] = None

def get_mongo_service(request: Request) -> MongoDBService:
    return request.app.state.mongo_service

def resolve_target_agent(action: str, category: str, group_agents_list: list) -> str:
    """
    Descobre o nome exato do agente baseado na categoria e ação.
    Agora com blindagem contra espaços em branco e diferenças de maiúsculas/minúsculas!
    """
    # Limpeza pesada nas entradas
    safe_action = str(action).strip().lower()
    safe_category = str(category).strip().lower()
    prefix = f"agent_{safe_category}_{safe_action}_"
    
    logger.info(f"🔍 [AgentResolver] Procurando prefixo: '{prefix}' na lista: {group_agents_list}")
    
    for agent_name in group_agents_list:
        # Limpa também o nome que veio do banco de dados
        safe_agent_name = str(agent_name).strip().lower()
        
        if safe_agent_name.startswith(prefix):
            logger.info(f"✅ [AgentResolver] Agente escolhido: '{agent_name}'")
            return agent_name
            
    logger.error(f"❌ [AgentResolver] Prefixo '{prefix}' não encontrado. Lista do grupo: {group_agents_list}")
    raise HTTPException(
        status_code=400, 
        detail=f"O grupo deste projeto não possui um agente configurado para {safe_action} de {safe_category}."
    )

async def get_historical_lineage(job_id: str, db) -> dict:
    context = {}
    queue = [job_id]
    visited = set()

    while queue:
        current_id = queue.pop(0)
        if current_id in visited:
            continue
        visited.add(current_id)

        report = await db.project_reports_history.find_one({"job_id": current_id})
        if not report:
            continue

        cat = report.get("report_category")
        if cat and cat not in context:
            context[cat] = current_id

        parent_context = report.get("context_used", {})
        for key, p_id in parent_context.items():
            if p_id:
                queue.append(p_id)

    return context
    
def validate_file_extension(file: UploadFile):
    extension = os.path.splitext(file.filename)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        log_validation_step(step="validate_file_extension", status="fail", details=f"Extensão '{extension}' não permitida.", job_id=None, project_id=None)
        logger.warning(f"Tentativa de upload de arquivo inválido: {file.filename}")
        raise HTTPException(status_code=400, detail=f"Extensão de arquivo '{extension}' não permitida. Use apenas: {', '.join(ALLOWED_EXTENSIONS)}")
    log_validation_step(step="validate_file_extension", status="success", details=f"Arquivo '{file.filename}' validado.", job_id=None, project_id=None)

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

async def get_or_create_project(
    nome_projeto: Optional[str], 
    email: str, 
    user, 
    company_id, 
    assigned_group_id: Optional[str], 
    mongo_service: MongoDBService
):
    if not nome_projeto:
        raise HTTPException(status_code=400, detail="Campos obrigatórios ausentes.")
    
    permission_service = PermissionService(mongo_service)
    nome_projeto_normalized = normalize_string_general(nome_projeto)
    project = await mongo_service.get_project_by_normalized_name(nome_projeto_normalized, company_id)
    
    if not project:
        can_create, error_msg_create = await permission_service.check_user_can_create_project(email, company_id)
        if not can_create:
            raise HTTPException(status_code=403, detail=error_msg_create)
            
        if not assigned_group_id:
            raise HTTPException(
                status_code=400, 
                detail="Para criar um novo projeto, é obrigatório informar o grupo de especialidade (assigned_group_id)."
            )
            
        new_project_id = str(uuid.uuid4()) 
        project_data = {
            "_id": new_project_id,
            "name": nome_projeto,
            "name_normalized": nome_projeto_normalized,
            "company_id": company_id,
            "assigned_group_id": assigned_group_id, # 🚀 SALVA O GRUPO AQUI
            "members": [{"user_id": user.id, "email": email, "role": "owner", "added_at": datetime.utcnow().isoformat()}],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "description": None
        }
        
        created_id = await mongo_service.create_project(project_data, company_id)
        if not created_id:
            raise HTTPException(status_code=500, detail="Erro de concorrência ao criar projeto.")
        project_id = created_id
        await RedisSessionService().invalidate_user_permissions(email, company_id)
    else:
        project_id = getattr(project, "id", None) or project.get("_id")
    
    return project_id, nome_projeto
    
@router.post("/start", response_model=StartAnalysisResponse, tags=["Analysis"])
async def start_analysis(
    email: Optional[str] = Form(None),
    nome_projeto: Optional[str] = Form(None),
    
    # 🚀 NOVOS PARÂMETROS FRONTEND 🚀
    category: str = Form(...), # "epics", "features", "timeline", "risks"
    action: str = Form(...),   # "generator", "reviwer"
    assigned_group_id: Optional[str] = Form(None), # Necessário apenas na criação do projeto
    branch: Optional[str] = Form(None),
    repository: Optional[str] = Form(None),
    comentario_extra: Optional[str] = Form(None),
    arquivo_docx: Optional[UploadFile] = File(None),
    base_job_id: Optional[str] = Form(None), 
    strategy: str = Form("checkout"),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    payload = {"email": email, "nome_projeto": nome_projeto, "category": category, "action": action, "base_job_id": base_job_id}
    log_request_received(endpoint="/analysis/start", payload=payload)

    if arquivo_docx: validate_file_extension(arquivo_docx)

    user, company_id = await validate_user_and_company(email, mongo_service)
    grupos_do_usuario = getattr(user, "group_ids", [])
    
    # 1. CRIA OU BUSCA O PROJETO (passando o grupo associado)
    project_id, nome_projeto_final = await get_or_create_project(
        nome_projeto, email, user, company_id, assigned_group_id, mongo_service
    )

    try:
        permission_service = PermissionService(mongo_service)
        has_permission, member_role, error_msg = await permission_service.check_user_project_action_permission(
            email, project_id, action_type="edit_project"
        )
        if not has_permission: raise HTTPException(status_code=403, detail=error_msg or "Sem permissão.")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao validar permissões do usuário.")

  # 🚀 2. BUSCA O PROJETO PARA PEGAR O GRUPO VINCULADO 🚀
    project_doc = await mongo_service.get_project_by_id(project_id)
    
    # 1º Tenta usar o grupo que o Frontend acabou de mandar (Criação de Projeto)
    project_group_id = assigned_group_id 
    
    # 2º Se não veio do front (Refinamento), tenta pegar do banco
    if not project_group_id:
        project_group_id = getattr(project_doc, "assigned_group_id", None)
        if project_group_id is None and isinstance(project_doc, dict):
            project_group_id = project_doc.get("assigned_group_id")
            
    if not project_group_id:
        raise HTTPException(status_code=400, detail="Este projeto não possui um grupo de especialidade associado.")

    # =====================================================================
    # 🚀 3. IDENTIFICA A ESPECIALIDADE DO PROJETO E O AGENTE NECESSÁRIO 🚀
    # =====================================================================
    project_group_doc = await mongo_service.db.groups.find_one({"_id": project_group_id})
    if not project_group_doc:
         raise HTTPException(status_code=404, detail=f"Grupo associado ({project_group_id}) não encontrado.")
         
    # Descobre o sufixo (ex: "digital", "sap") a partir dos agentes do grupo original do projeto
    project_agents = project_group_doc.get("allowed_agents", [])
    project_suffix = "digital" # Fallback de segurança
    for pa in project_agents:
        parts = str(pa).strip().split("_")
        if len(parts) >= 4:
            project_suffix = parts[-1]
            break

    # Monta o nome exato do agente que o sistema precisa invocar agora:
    target_agent_name = f"agent_{str(category).strip().lower()}_{str(action).strip().lower()}_{project_suffix}"
    logger.info(f"🎯 [AgentResolver] O projeto exige o agente: '{target_agent_name}'")

    # =====================================================================
    # 🚀 4. VERIFICA SE O *USUÁRIO LOGADO* TEM PERMISSÃO PARA ESSE AGENTE 🚀
    # =====================================================================
    user_group_ids = getattr(user, "group_ids", [])
    user_groups_cursor = mongo_service.db.groups.find({"_id": {"$in": user_group_ids}})
    user_groups = await user_groups_cursor.to_list(length=100)
    
    # Junta todos os agentes de todos os grupos do usuário atual (O Rafael)
    user_allowed_agents = set()
    for g in user_groups:
         for agent in g.get("allowed_agents", []):
             user_allowed_agents.add(str(agent).strip().lower())
             
    logger.info(f"👤 [AgentResolver] Agentes disponíveis para o usuário {email}: {list(user_allowed_agents)}")

    # A grande validação: O usuário tem a ferramenta certa na mochila?
    if target_agent_name not in user_allowed_agents:
         raise HTTPException(
             status_code=403, 
             detail=f"Seu usuário não possui permissão para utilizar o agente '{target_agent_name}' necessário para esta etapa."
         )
         
    # Passou na validação! Define o agente final para enviar ao MCP
    analysis_type = target_agent_name

    # 5. VALIDA O AGENTE NO MCP
    agent_cfg = MCPConfigService.get_agent_config(analysis_type)
    if not agent_cfg or not agent_cfg.mcp_service_url:
        raise HTTPException(status_code=500, detail=f"Agente '{analysis_type}' indisponível no serviço MCP.")

    # ==========================================
    # 6. CONSTRUÇÃO DO CONTEXTO DE LINHAGEM 
    # ==========================================
    reports_to_read = CATEGORY_DEPENDENCIES.get(category, [])
    context_used = {}

    latest_reports_db = getattr(project_doc, "latest_reports", {})
    if not isinstance(latest_reports_db, dict) and hasattr(latest_reports_db, "dict"):
        latest_reports_db = latest_reports_db.dict()
    elif not latest_reports_db:
        latest_reports_db = {}

    if base_job_id:
        past_report = await mongo_service.db.project_reports_history.find_one({"job_id": base_job_id})
        if not past_report: raise HTTPException(status_code=404, detail="Relatório base não encontrado.")
            
        target_category = past_report.get("report_category")
        historical_tree = await get_historical_lineage(base_job_id, mongo_service.db)
        
        for cat in reports_to_read:
            if cat == target_category:
                context_used[f"{cat}_job_id"] = base_job_id
            else:
                if strategy == "rebase":
                    dependency_job_id = latest_reports_db.get(cat) or historical_tree.get(cat)
                else:
                    dependency_job_id = historical_tree.get(cat) or latest_reports_db.get(cat)
                
                if not dependency_job_id: raise HTTPException(status_code=400, detail=f"Dependência '{cat}' não encontrada.")
                context_used[f"{cat}_job_id"] = dependency_job_id

        if strategy == "checkout":
            new_latest_state = {}
            for cat, j_id in context_used.items():
                cat_name = cat.replace("_job_id", "")
                new_latest_state[cat_name] = j_id
            await mongo_service.update_project_latest_reports(project_id, new_latest_state)

    else:
        for cat in reports_to_read:
            dependency_job_id = latest_reports_db.get(cat)
            if not dependency_job_id: raise HTTPException(status_code=400, detail=f"Dependência '{cat}' não encontrada para gerar {category}.")
            context_used[f"{cat}_job_id"] = dependency_job_id

    # 7. EXECUÇÃO
    job_id = str(uuid.uuid4())
    redis_service = RedisSessionService()
    job_id = await redis_service.create_job(
        project_id=project_id, analysis_type=analysis_type, email=email, empresa=company_id, context_used=context_used
    )
    
    mcp_payload = {
        "email": email, "nome_projeto": nome_projeto_final, "analysis_type": analysis_type,
        "branch": branch, "repository": repository, "comentario_extra": comentario_extra,
        "project_id": project_id, "job_id": job_id, "company_id": company_id,
        "group_ids": grupos_do_usuario, "context_used": context_used
    }
    
    mcp_client = MCPClientService(base_url=agent_cfg.mcp_service_url)
    try:
        await mcp_client.start_analysis(mcp_payload, agent_cfg.mcp_service_url, arquivo_docx)
    except Exception as e:
        logger.error(f"Erro MCP {job_id}: {e}")
        raise HTTPException(status_code=502, detail=f"Erro no MCP: {str(e)}")

    response_obj = StartAnalysisResponse(
        message="Análise multiagente solicitada com sucesso ao MCP.",
        project_id=project_id, job_id=job_id, nome_projeto=nome_projeto_final
    )
    return response_obj

# ============================================================================
# 🚀 ROTA DO GRAFO (ÁRVORE DE LINHAGEM DO PROJETO) - CORRIGIDA! 🚀
# ============================================================================
@router.get("/lineage/{project_id}", tags=["Lineage"])
async def get_project_lineage(project_id: str, mongo_service: MongoDBService = Depends(get_mongo_service)):
    cursor = mongo_service.db.project_reports_history.find({"project_id": project_id}).sort("created_at", 1) 
    history = await cursor.to_list(length=2000)
    if not history: return {"nodes": [], "edges": []}

    nodes = []
    edges = []
    job_category_map = {item["job_id"]: item.get("report_category") for item in history}

    # 🚀 MÁGICA AQUI: Memória para rastrear a versão anterior de cada categoria
    last_version_map = {}

    for report in history:
        job_id = report.get("job_id")
        category = report.get("report_category", "unknown")
        version = report.get("version", 1)
        
        nodes.append({
            "id": job_id, "type": category, "label": f"{str(category).capitalize()} v{version}",
            "version": version, "status": report.get("status"),
            "created_at": report.get("created_at").isoformat() if getattr(report.get("created_at"), "isoformat", None) else str(report.get("created_at")),
            "created_by": report.get("created_by_email")
        })

        context_used = report.get("context_used", {})
        has_refinement_edge = False

        # 1. Cria as arestas de DEPENDÊNCIA (Ex: Epic -> Feature)
        for ctx_key, parent_job_id in context_used.items():
            if not parent_job_id: continue
            parent_category = job_category_map.get(parent_job_id)
            
            if parent_category == category:
                edge_type = "refinement"
                has_refinement_edge = True
            else:
                edge_type = "dependency"
                
            edges.append({
                "id": f"edge_{parent_job_id}_to_{job_id}", 
                "source": parent_job_id, 
                "target": job_id, 
                "type": edge_type
            })

        # 2. Cria as arestas de REFINAMENTO (Ex: Epics v1 -> Epics v2)
        # Se for uma evolução e o context_used não tiver pego, ligamos manualmente à versão anterior.
        if not has_refinement_edge and category in last_version_map:
            parent_job_id = last_version_map[category]
            edges.append({
                "id": f"edge_auto_refine_{parent_job_id}_to_{job_id}",
                "source": parent_job_id,
                "target": job_id,
                "type": "refinement"
            })

        # Atualiza a memória com o ID atual para que a próxima versão (v3) saiba de onde puxar
        last_version_map[category] = job_id

    return {"project_id": project_id, "nodes": nodes, "edges": edges}

# ============================================================================
# ROTA DE RESTAURAÇÃO DE VERSÃO (ROLLBACK / GIT RESET)
# ============================================================================
@router.post("/restore", tags=["Analysis"])
async def restore_historical_version(project_id: str = Form(...), job_id: str = Form(...), mongo_service: MongoDBService = Depends(get_mongo_service)):
    report = await mongo_service.db.project_reports_history.find_one({"job_id": job_id})
    if not report: raise HTTPException(status_code=404, detail="Relatório histórico não encontrado.")

    historical_tree = await get_historical_lineage(job_id, mongo_service.db)
    new_latest_state = {}
    for cat, j_id in historical_tree.items():
        cat_name = cat.replace("_job_id", "") 
        new_latest_state[cat_name] = j_id

    target_category = report.get("report_category")
    new_latest_state[target_category] = job_id

    success = await mongo_service.update_project_latest_reports(project_id, new_latest_state)
    if not success: raise HTTPException(status_code=500, detail="Falha ao atualizar o banco de dados.")

    return {"message": "Versão e contexto restaurados com sucesso.", "new_state": new_latest_state}
