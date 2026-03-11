import logging
from datetime import datetime
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query, Body, Depends, status, Path

from backend.app.services.mongodb_service import MongoDBService
from backend.app.services.permission_service import PermissionService
from backend.app.models.project_management_models import (
    ListOwnedProjectsResponse,
    ProjectWithRoleItem,
    OwnedProjectItem,
    AddProjectMemberRequest,
    AddProjectMemberResponse,
    UpdateProjectMembersRequest,
    UpdateProjectMembersResponse,
    RemoveMemberRequest,
    DeleteProjectRequest,
    DeleteProjectResponse,
    ProjectRole,
    ProjectDetailsResponse,
    LatestReports,
    ReportHistoryItem,
    ReportHistoryResponse,
    ReportLineageResponse
)
from backend.app.services.redis_session_service import RedisSessionService

router = APIRouter()
logger = logging.getLogger("project_management_api")

# Helper para Injeção de Dependência
def get_mongo_service():
    return MongoDBService()

@router.get("/list", response_model=List[ProjectWithRoleItem], tags=["Project Management"])
async def list_all_user_projects(
    email: str = Query(..., description="Email do usuário"),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    """Lista TODOS os projetos que o usuário tem acesso."""
    logger.info(f"[ProjectList] Buscando projetos para: {email}")
    projects = await mongo_service.get_user_projects_with_access(email)
    if not projects:
        return []
    return projects

@router.get("/{project_id}", response_model=ProjectDetailsResponse, tags=["Project Management"])
async def get_project_details(
    project_id: str = Path(..., description="ID do projeto"),
    email: str = Query(..., description="Email do usuário solicitante"),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    """Retorna os detalhes de um projeto específico."""
    logger.info(f"[ProjectManagement] Buscando detalhes do projeto {project_id} para {email}")

    project = await mongo_service.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    members = getattr(project, "members", []) if not isinstance(project, dict) else project.get("members", [])
    
    is_member = False
    for m in members:
        m_email = getattr(m, "email", None) if not isinstance(m, dict) else m.get("email")
        if m_email == email:
            is_member = True
            break

    if not is_member:
        logger.warning(f"[ProjectManagement] Acesso negado: {email} tentou ler o projeto {project_id}")
        raise HTTPException(status_code=403, detail="Você não tem permissão para visualizar este projeto.")

    proj_id_str = str(getattr(project, "id", None) or getattr(project, "_id", project_id)) if not isinstance(project, dict) else str(project.get("_id", project_id))
    comp_id_str = str(getattr(project, "company_id", "")) if not isinstance(project, dict) else str(project.get("company_id", ""))
    name = getattr(project, "name", "") if not isinstance(project, dict) else project.get("name", "")
    desc = getattr(project, "description", None) if not isinstance(project, dict) else project.get("description")
    
    reports_data = getattr(project, "latest_reports", {}) if not isinstance(project, dict) else project.get("latest_reports", {})
    if not reports_data:
        reports_data = {}
    elif not isinstance(reports_data, dict):
        reports_data = reports_data.dict() 

    return ProjectDetailsResponse(
        project_id=proj_id_str,
        name=name,
        description=desc,
        company_id=comp_id_str,
        latest_reports=LatestReports(**reports_data)
    )
    
@router.get("/owned", response_model=ListOwnedProjectsResponse, tags=["Project Management"])
async def list_owned_projects(
    email: str = Query(..., description="Email do usuário owner"),
    mongo_service: MongoDBService = Depends(get_mongo_service) 
):
    logger.info(f"[ProjectManagement] Recebida requisição para /projects/owned com email={email}")
    
    user = await mongo_service.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        
    company_id = getattr(user, "company_id", None)
    if not company_id:
        raise HTTPException(status_code=400, detail="Usuário não possui company_id.")
        
    projects = await mongo_service.get_projects_where_user_is_owner(email, company_id=company_id)
    
    items = [OwnedProjectItem(
        project_id=p["project_id"],
        name=p["name"],
        description=p.get("description"),
        members=p.get("members", [])
    ) for p in projects]
    
    return ListOwnedProjectsResponse(projects=items)

@router.post("/members", response_model=AddProjectMemberResponse, tags=["Project Management"])
async def add_project_member(
    req: AddProjectMemberRequest = Body(...),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    logger.info(f"[ProjectManagement] Adicionar membro: requester={req.requester_email}, projeto_id={req.project_id}")
    
    user = await mongo_service.get_user_by_email(req.requester_email)
    if not user:
        return AddProjectMemberResponse(success=False, message="Usuário requisitante não encontrado.")
    company_id = getattr(user, "company_id", None)
    
    project_id = req.project_id
    project = await mongo_service.get_project_by_id(project_id)
    if not project or getattr(project, "company_id", None) != company_id:
        return AddProjectMemberResponse(success=False, message="Projeto não encontrado nesta empresa.")

    permission_service = PermissionService(mongo_service)
    redis_session_service = RedisSessionService()
    
    try:
        has_perm, _, error_msg = await permission_service.check_user_project_action_permission(
            req.requester_email, project_id, action_type="add_member"
        )
        if not has_perm:
            return AddProjectMemberResponse(success=False, message=error_msg or "Sem permissão.")
            
        if not await _verify_user_is_owner_helper(req.requester_email, project_id, mongo_service):
             return AddProjectMemberResponse(success=False, message="Apenas Owners podem adicionar membros.")
             
        new_user = await mongo_service.get_user_by_email(req.new_member_email)
        if not new_user:
            return AddProjectMemberResponse(success=False, message="Usuário a ser adicionado não encontrado.")
            
        # 🚀 VALIDAÇÃO 1: SEGURANÇA (ISOLAMENTO MULTI-TENANT)
        new_user_company_id = getattr(new_user, "company_id", None)
        if str(new_user_company_id) != str(company_id):
            logger.warning(f"[ProjectManagement] Tentativa bloqueada: O usuário {req.new_member_email} não pertence à empresa do projeto {project_id}.")
            return AddProjectMemberResponse(success=False, message="Ação negada: Este usuário não pertence à mesma empresa deste projeto.")
        
        # ==========================================================
        # 🚀 VALIDAÇÃO 2: REGRA DE NEGÓCIO DE GRUPOS (OWNER/EDITOR)
        # ==========================================================
        requested_role = str(req.role.value).lower()
        
        if requested_role in ["owner", "editor"]:
            # Pega o ID do grupo do projeto com segurança
            project_group_id = getattr(project, "assigned_group_id", None)
            if not project_group_id and isinstance(project, dict):
                project_group_id = project.get("assigned_group_id")
            project_group_id = str(project_group_id) if project_group_id else ""

            # Pega a lista de grupos do novo usuário com segurança
            new_user_groups_raw = getattr(new_user, "group_ids", [])
            if not new_user_groups_raw and isinstance(new_user, dict):
                new_user_groups_raw = new_user.get("group_ids", [])
            new_user_groups = [str(g) for g in new_user_groups_raw]

            # Se o projeto tem um grupo, mas o usuário não pertence a ele, bloqueia!
            if project_group_id and project_group_id not in new_user_groups:
                logger.warning(f"[ProjectManagement] Bloqueio de Role: {req.new_member_email} tentou ser {requested_role}, mas não possui o grupo {project_group_id}.")
                return AddProjectMemberResponse(
                    success=False, 
                    message=f"O usuário {req.new_member_email} não pertence à especialidade (grupo) deste projeto. Portanto, ele só pode ser adicionado como 'Leitor (Viewer)'."
                )
        # ==========================================================

        new_member = {
            "user_id": str(getattr(new_user, "id", None) or new_user.get("_id")),
            "email": req.new_member_email,
            "role": req.role.value,
            "added_at": datetime.utcnow().isoformat()
        }
        result = await mongo_service.add_member_to_project(project_id, new_member)
        await redis_session_service.invalidate_user_permissions(req.new_member_email, company_id)
        
        return AddProjectMemberResponse(
            success=bool(result), 
            message="Membro adicionado!" if result else "Erro ao adicionar."
        )
    except Exception as e:
        logger.error(f"Erro add_project_member: {e}")
        return AddProjectMemberResponse(success=False, message=str(e))

@router.put("/members", response_model=UpdateProjectMembersResponse, tags=["Project Management"])
async def update_project_members(
    req: UpdateProjectMembersRequest = Body(...),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    logger.info(f"[ProjectManagement] Atualizar membros: requester={req.requester_email}, projeto_id={req.project_id}")
    
    user = await mongo_service.get_user_by_email(req.requester_email)
    if not user:
        return UpdateProjectMembersResponse(success=False, message="Usuário requisitante não encontrado.")
    company_id = getattr(user, "company_id", None)
    
    project_id = req.project_id
    project = await mongo_service.get_project_by_id(project_id)
    if not project or getattr(project, "company_id", None) != company_id:
        return UpdateProjectMembersResponse(success=False, message="Projeto não encontrado nesta empresa.")

    permission_service = PermissionService(mongo_service)
    redis_session_service = RedisSessionService()
    try:
        has_perm, _, error_msg = await permission_service.check_user_project_action_permission(
            req.requester_email, project_id, action_type="edit_project"
        )
        if not has_perm:
            return UpdateProjectMembersResponse(success=False, message=error_msg)
            
        if not await _verify_user_is_owner_helper(req.requester_email, project_id, mongo_service):
            return UpdateProjectMembersResponse(success=False, message="Apenas Owners podem gerenciar membros.")
            
        incoming_owners = [m for m in req.members if m.get("role", "").lower() == "owner"]
        if not incoming_owners:
            return UpdateProjectMembersResponse(
                success=False, 
                message="Ação negada: A lista de membros deve conter pelo menos um Owner."
            )
            
        requester_in_new_list = next((m for m in req.members if m.get("email") == req.requester_email), None)
        if not requester_in_new_list:
             return UpdateProjectMembersResponse(
                success=False, 
                message="Você não pode se remover da lista via atualização. Use a função de sair do projeto."
            )
            
        if requester_in_new_list.get("role", "").lower() != "owner":
            other_owners = [m for m in incoming_owners if m.get("email") != req.requester_email]
            if not other_owners:
                return UpdateProjectMembersResponse(
                    success=False, 
                    message="Você não pode alterar seu nível para Editor/Viewer sem antes promover outro membro a Owner."
                )
                
        result = await mongo_service.update_project_members(project_id, req.members)
        
        affected_emails = [m.get("email") for m in req.members if m.get("email")]
        for email in set(affected_emails):
            await redis_session_service.invalidate_user_permissions(email, company_id)
            
        return UpdateProjectMembersResponse(
            success=bool(result), 
            message="Membros atualizados com sucesso!" if result else "Falha na atualização."
        )
    except Exception as e:
        logger.error(f"Erro update_project_members: {e}")
        return UpdateProjectMembersResponse(success=False, message=str(e))

@router.get("/{project_id}/members", tags=["Project Management"])
async def get_project_members(
    project_id: str = Path(..., description="ID do projeto"),
    email: str = Query(..., description="Email do usuário solicitante"),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    """Retorna a lista fresquinha e atualizada de membros do projeto."""
    project = await mongo_service.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    members = getattr(project, "members", []) if not isinstance(project, dict) else project.get("members", [])
    
    # Trava de Segurança: Só devolve a lista se quem está pedindo fizer parte do projeto
    is_member = any((getattr(m, "email", None) if not isinstance(m, dict) else m.get("email")) == email for m in members)
    if not is_member:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    members_list = [m if isinstance(m, dict) else m.dict() for m in members]
    return {"members": members_list}

@router.delete("/members/{target_email}", tags=["Project Management"])
async def remove_project_member(
    target_email: str,
    req: RemoveMemberRequest = Body(...),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    logger.info(f"[ProjectManagement] Remove Member: target={target_email}, requester={req.requester_email}, projeto_id={req.project_id}")
    
    user = await mongo_service.get_user_by_email(req.requester_email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário requisitante não encontrado.")
    company_id = getattr(user, "company_id", None)
    
    project_id = req.project_id
    
    permission_service = PermissionService(mongo_service)
    redis_session_service = RedisSessionService()
    
    has_perm, _, error_msg = await permission_service.check_user_project_action_permission(
        req.requester_email, project_id, action_type="remove_member"
    )
    if not has_perm:
        raise HTTPException(status_code=403, detail=error_msg)
        
    project = await mongo_service.get_project_by_id(project_id)
    if not project or getattr(project, "company_id", None) != company_id:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
        
    target_member = next((m for m in project.members if m.email == target_email), None)
    if target_member and target_member.role.lower() == "owner":
        owners = [m for m in project.members if m.role.lower() == "owner"]
        if len(owners) <= 1:
            raise HTTPException(
                status_code=400, 
                detail="Não é possível remover o único dono do projeto. Adicione outro dono antes de remover este."
            )
            
    success = await mongo_service.remove_member_from_project(project_id, target_email)
    await redis_session_service.invalidate_user_permissions(target_email, company_id)
    await redis_session_service.invalidate_user_permissions(req.requester_email, company_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Falha ao remover membro no banco de dados.")
    return {"success": True, "message": f"Membro {target_email} removido com sucesso."}

@router.delete("/delete", response_model=DeleteProjectResponse, tags=["Project Management"])
async def delete_project(
    req: DeleteProjectRequest = Body(...),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    """Remove permanentemente um projeto do banco de dados."""
    logger.info(f"[ProjectManagement] Tentativa de exclusão: requester={req.requester_email}, projeto_id={req.project_id}")
    
    user = await mongo_service.get_user_by_email(req.requester_email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário requisitante não encontrado.")
    company_id = getattr(user, "company_id", None)
    if not company_id:
        raise HTTPException(status_code=400, detail="Usuário requisitante não possui company_id.")
        
    project_id = req.project_id
    permission_service = PermissionService(mongo_service)
    redis_session_service = RedisSessionService()
    
    try:
        has_permission, _, error_msg = await permission_service.check_user_project_action_permission(
            req.requester_email, project_id, action_type="delete_project"
        )
        if not has_permission:
            logger.warning(f"[ProjectManagement] Acesso negado para exclusão: {req.requester_email}")
            raise HTTPException(status_code=403, detail=error_msg or "Permissão negada.")
            
        project = await mongo_service.get_project_by_id(project_id)
        if not project or getattr(project, "company_id", None) != company_id:
            return DeleteProjectResponse(success=False, message="Projeto não encontrado.")
            
        affected_emails = [m.email for m in project.members] if project.members else []
        
        success = await mongo_service.delete_project(project_id, company_id)
        if success:
            for email in set(affected_emails):
                await redis_session_service.invalidate_user_permissions(email, company_id)
            await redis_session_service.invalidate_user_permissions(req.requester_email, company_id)
            logger.info(f"[ProjectManagement] Projeto {project_id} excluído com sucesso.")
            return DeleteProjectResponse(success=True, message="Projeto excluído com sucesso.")
            
        return DeleteProjectResponse(success=False, message="Erro ao excluir projeto ou projeto já excluído.")
    except HTTPException as hex:
        raise hex
    except Exception as e:
        logger.error(f"[ProjectManagement] Erro crítico na exclusão: {e}")
        return DeleteProjectResponse(success=False, message=f"Erro interno: {str(e)}")


# --- Helpers Locais ---
async def _verify_user_is_owner_helper(email: str, project_id: str, mongo_service: MongoDBService) -> bool:
    project = await mongo_service.get_project_by_id(project_id)
    if not project:
        return False
    return any(m.email == email and m.role.lower() == ProjectRole.OWNER.value for m in project.members)


@router.get("/{project_id}/reports/history", response_model=ReportHistoryResponse, tags=["Project Management"])
async def get_report_history(
    project_id: str = Path(..., description="ID do projeto"),
    category: str = Query(..., description="Categoria do relatório (ex: epics, features)"),
    email: str = Query(..., description="Email do usuário solicitante"),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    """Lista o histórico de versões de uma categoria de relatório (ex: epics) para um projeto específico."""
    logger.info(f"[ProjectManagement] Buscando histórico de '{category}' para o projeto {project_id} (User: {email})")

    project = await mongo_service.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    members = getattr(project, "members", []) if not isinstance(project, dict) else project.get("members", [])
    is_member = any((getattr(m, "email", None) if not isinstance(m, dict) else m.get("email")) == email for m in members)
    
    if not is_member:
        logger.warning(f"[ProjectManagement] Acesso negado: {email} tentou ver histórico do projeto {project_id}")
        raise HTTPException(status_code=403, detail="Você não tem permissão para visualizar este projeto.")

    try:
        obj_project_id = ObjectId(project_id)
    except Exception:
        obj_project_id = project_id

    cursor = mongo_service.db.project_reports_history.find({
        "project_id": obj_project_id,
        "report_category": category,
        "status": "done" 
    }).sort("version", -1)

    historico = []
    async for doc in cursor:
        historico.append(ReportHistoryItem(
            job_id=doc.get("job_id"),
            project_id=str(doc.get("project_id")), 
            report_category=doc.get("report_category"),
            analysis_type=doc.get("analysis_type"),
            version=doc.get("version", 1),
            status=doc.get("status"),
            created_by_email=doc.get("created_by_email", "Desconhecido"),
            created_at=doc.get("created_at"),
            context_used=doc.get("context_used", {}),
            blob_path=doc.get("blob_path")
        ))
    return ReportHistoryResponse(history=historico)

@router.get("/{project_id}/reports/{job_id}/lineage", response_model=ReportLineageResponse, tags=["Project Management"])
async def get_report_lineage(
    project_id: str = Path(..., description="ID do projeto"),
    job_id: str = Path(..., description="ID do Job base"),
    category: str = Query(..., description="A categoria do relatório atual"),
    email: str = Query(..., description="Email do usuário solicitante"),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    """Retorna a árvore genealógica (Ancestrais e Descendentes) de um relatório específico."""
    logger.info(f"[ProjectManagement] Buscando linhagem do Job {job_id} (Categoria: {category}) no projeto {project_id}")

    project = await mongo_service.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    members = getattr(project, "members", []) if not isinstance(project, dict) else project.get("members", [])
    is_member = any((getattr(m, "email", None) if not isinstance(m, dict) else m.get("email")) == email for m in members)
    
    if not is_member:
        raise HTTPException(status_code=403, detail="Você não tem permissão para visualizar este projeto.")

    tree_data = await mongo_service.get_report_context_tree(project_id, job_id, category)
    
    if not tree_data:
        raise HTTPException(status_code=404, detail="Relatório base não encontrado no histórico.")

    def format_history_item(doc: dict) -> Optional[dict]:
        if not doc: return None
        doc.pop("_id", None)
        if "project_id" in doc and not isinstance(doc["project_id"], str):
            doc["project_id"] = str(doc["project_id"])
        if "created_by_email" not in doc: doc["created_by_email"] = "Desconhecido"
        return doc

    return ReportLineageResponse(
        epics=format_history_item(tree_data.get("epics")),
        features=format_history_item(tree_data.get("features")),
        timeline=format_history_item(tree_data.get("timeline")),
        risks=format_history_item(tree_data.get("risks")),
        prototype=format_history_item(tree_data.get("prototype"))
    )
