import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Body, Depends, status

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
    DeleteProjectRequest,
    DeleteProjectResponse,
    ProjectRole,
    ProjectDetailsResponse,
    LatestReports
)
from backend.app.services.redis_session_service import RedisSessionService

router = APIRouter()
logger = logging.getLogger("project_management_api")

# Helper para Injeção de Dependência
def get_mongo_service():
    return MongoDBService()

async def resolve_project_id_by_name(project_name: str, company_id: str, mongo_service: MongoDBService) -> str:
    project = await mongo_service.get_project_by_normalized_name(project_name, company_id)
    if not project:
        logger.error(f"[ProjectManagement] Projeto '{project_name}' não encontrado para empresa '{company_id}'.")
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    return getattr(project, "id", None) or project._id

@router.get("/list", response_model=List[ProjectWithRoleItem], tags=["Project Management"])
async def list_all_user_projects(
    email: str = Query(..., description="Email do usuário"),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    """
    Lista TODOS os projetos que o usuário tem acesso.
    Retorna também o 'role' (nível de acesso) específico do usuário naquele projeto.
    """
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
    """
    Retorna os detalhes de um projeto específico, incluindo o ponteiro para os relatórios mais recentes.
    """
    logger.info(f"[ProjectManagement] Buscando detalhes do projeto {project_id} para {email}")

    # 1. Busca o projeto no banco
    project = await mongo_service.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    # 2. Segurança: Verifica se o usuário pertence a este projeto
    # Trata de forma segura caso 'project' venha como Dicionário ou como Objeto (Pydantic)
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

    # 3. Extração segura de dados (lidando com ObjectId e diferenças estruturais)
    proj_id_str = str(getattr(project, "id", None) or getattr(project, "_id", project_id)) if not isinstance(project, dict) else str(project.get("_id", project_id))
    comp_id_str = str(getattr(project, "company_id", "")) if not isinstance(project, dict) else str(project.get("company_id", ""))
    name = getattr(project, "name", "") if not isinstance(project, dict) else project.get("name", "")
    desc = getattr(project, "description", None) if not isinstance(project, dict) else project.get("description")
    
    # Busca o ponteiro de relatórios
    reports_data = getattr(project, "latest_reports", {}) if not isinstance(project, dict) else project.get("latest_reports", {})
    if not reports_data:
        reports_data = {}
    elif not isinstance(reports_data, dict):
        reports_data = reports_data.dict() # Converte caso o banco devolva um modelo interno

    # 4. Retorna no formato esperado pelo Front-end
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
    mongo_service: MongoDBService = Depends(get_mongo_service) # <--- O serviço entra aqui
):
    logger.info(f"[ProjectManagement] Recebida requisição para /projects/owned com email={email}")
    
    user = await mongo_service.get_user_by_email(email)
    if not user:
        logger.error(f"[ProjectManagement] Usuário não encontrado: email={email}")
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        
    company_id = getattr(user, "company_id", None)
    if not company_id:
        logger.error(f"[ProjectManagement] Usuário não possui company_id: email={email}")
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
    logger.info(f"[ProjectManagement] Adicionar membro: requester={req.requester_email}, projeto={req.project_name}")
    # Resolve company_id do requester
    user = await mongo_service.get_user_by_email(req.requester_email)
    if not user:
        logger.error(f"[ProjectManagement] Usuário requisitante não encontrado: {req.requester_email}")
        return AddProjectMemberResponse(success=False, message="Usuário requisitante não encontrado.")
    company_id = getattr(user, "company_id", None)
    if not company_id:
        logger.error(f"[ProjectManagement] Usuário requisitante não possui company_id: {req.requester_email}")
        return AddProjectMemberResponse(success=False, message="Usuário requisitante não possui company_id.")
    # Resolve project_id
    project_id = await resolve_project_id_by_name(req.project_name, company_id, mongo_service)
    permission_service = PermissionService(mongo_service)
    redis_session_service = RedisSessionService()
    try:
        # 1. Validação de permissão
        has_perm, _, error_msg = await permission_service.check_user_project_action_permission(
            req.requester_email, project_id, action_type="add_member"
        )
        if not has_perm:
            return AddProjectMemberResponse(success=False, message=error_msg or "Sem permissão.")
        # 2. Validação extra de Ownership
        if not await _verify_user_is_owner_helper(req.requester_email, project_id, mongo_service):
             return AddProjectMemberResponse(success=False, message="Apenas Owners podem adicionar membros.")
        # 3. Busca novo membro
        new_user = await mongo_service.get_user_by_email(req.new_member_email)
        if not new_user:
            return AddProjectMemberResponse(success=False, message="Usuário a ser adicionado não encontrado.")
        new_member = {
            "user_id": str(new_user.id),
            "email": req.new_member_email,
            "role": req.role.value,
            "added_at": datetime.utcnow().isoformat()
        }
        result = await mongo_service.add_member_to_project(project_id, new_member)
        # Cache invalidation
        project = await mongo_service.get_project_by_id(project_id)
        if project:
            company_id = getattr(project, "company_id", None)
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
    logger.info(f"[ProjectManagement] Atualizar membros: requester={req.requester_email}, projeto={req.project_name}")
    # Resolve company_id do requester
    user = await mongo_service.get_user_by_email(req.requester_email)
    if not user:
        logger.error(f"[ProjectManagement] Usuário requisitante não encontrado: {req.requester_email}")
        return UpdateProjectMembersResponse(success=False, message="Usuário requisitante não encontrado.")
    company_id = getattr(user, "company_id", None)
    if not company_id:
        logger.error(f"[ProjectManagement] Usuário requisitante não possui company_id: {req.requester_email}")
        return UpdateProjectMembersResponse(success=False, message="Usuário requisitante não possui company_id.")
    # Resolve project_id
    project_id = await resolve_project_id_by_name(req.project_name, company_id, mongo_service)
    permission_service = PermissionService(mongo_service)
    redis_session_service = RedisSessionService()
    try:
        # 1. Verifica permissão básica de edição
        has_perm, _, error_msg = await permission_service.check_user_project_action_permission(
            req.requester_email, project_id, action_type="edit_project"
        )
        if not has_perm:
            return UpdateProjectMembersResponse(success=False, message=error_msg)
        # 2. Verifica se quem pede é Owner
        if not await _verify_user_is_owner_helper(req.requester_email, project_id, mongo_service):
            return UpdateProjectMembersResponse(success=False, message="Apenas Owners podem gerenciar membros.")
        # Identifica os owners na NOVA lista
        incoming_owners = [m for m in req.members if m.get("role", "").lower() == "owner"]
        if not incoming_owners:
            return UpdateProjectMembersResponse(
                success=False, 
                message="Ação negada: A lista de membros deve conter pelo menos um Owner."
            )
        requester_in_new_list = next(
            (m for m in req.members if m.get("email") == req.requester_email), None
        )
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
        project = await mongo_service.get_project_by_id(project_id)
        if project:
            company_id = getattr(project, "company_id", None)
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

from pydantic import BaseModel, EmailStr
class RemoveMemberRequest(BaseModel):
    requester_email: EmailStr
    project_name: str
    target_email: EmailStr

@router.delete("/members/{target_email}", tags=["Project Management"])
async def remove_project_member(
    target_email: str,
    req: RemoveMemberRequest = Body(...),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    logger.info(f"[ProjectManagement] Remove Member: target={target_email}, requester={req.requester_email}, projeto={req.project_name}")
    # Resolve company_id do requester
    user = await mongo_service.get_user_by_email(req.requester_email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário requisitante não encontrado.")
    company_id = getattr(user, "company_id", None)
    if not company_id:
        raise HTTPException(status_code=400, detail="Usuário requisitante não possui company_id.")
    # Resolve project_id
    project_id = await resolve_project_id_by_name(req.project_name, company_id, mongo_service)
    permission_service = PermissionService(mongo_service)
    redis_session_service = RedisSessionService()
    # 1. Verifica Permissão
    has_perm, _, error_msg = await permission_service.check_user_project_action_permission(
        req.requester_email, project_id, action_type="remove_member"
    )
    if not has_perm:
        raise HTTPException(status_code=403, detail=error_msg)
    project = await mongo_service.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    # 2. Validação: Não permitir remover o último owner
    target_member = next((m for m in project.members if m.email == target_email), None)
    if target_member and target_member.role.lower() == "owner":
        owners = [m for m in project.members if m.role.lower() == "owner"]
        if len(owners) <= 1:
            raise HTTPException(
                status_code=400, 
                detail="Não é possível remover o único dono do projeto. Adicione outro dono antes de remover este."
            )
    success = await mongo_service.remove_member_from_project(project_id, target_email)
    company_id = getattr(project, "company_id", None)
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
    """
    Remove permanentemente um projeto do banco de dados.
    """
    logger.info(f"[ProjectManagement] Tentativa de exclusão: requester={req.requester_email}, projeto={req.project_name}")
    user = await mongo_service.get_user_by_email(req.requester_email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário requisitante não encontrado.")
    company_id = getattr(user, "company_id", None)
    if not company_id:
        raise HTTPException(status_code=400, detail="Usuário requisitante não possui company_id.")
    project_id = await resolve_project_id_by_name(req.project_name, company_id, mongo_service)
    permission_service = PermissionService(mongo_service)
    redis_session_service = RedisSessionService()
    try:
        # 1. Verifica permissão de deletar
        has_permission, _, error_msg = await permission_service.check_user_project_action_permission(
            req.requester_email, project_id, action_type="delete_project"
        )
        if not has_permission:
            logger.warning(f"[ProjectManagement] Acesso negado para exclusão: {req.requester_email}")
            raise HTTPException(status_code=403, detail=error_msg or "Permissão negada.")
        # 2. Pega dados para limpar cache depois
        project = await mongo_service.get_project_by_id(project_id)
        if not project:
            return DeleteProjectResponse(success=False, message="Projeto não encontrado.")
        company_id = getattr(project, "company_id", None)
        affected_emails = [m.email for m in project.members] if project.members else []
        # 3. Deleta 
        success = await mongo_service.delete_project(project_id, company_id)
        # 4. Limpa Cache
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

# --- Helpers Locais (Renomeado para evitar conflito e ser interno) ---
async def _verify_user_is_owner_helper(email: str, project_id: str, mongo_service: MongoDBService) -> bool:
    project = await mongo_service.get_project_by_id(project_id)
    if not project:
        return False
    return any(m.email == email and m.role.lower() == ProjectRole.OWNER.value for m in project.members)
