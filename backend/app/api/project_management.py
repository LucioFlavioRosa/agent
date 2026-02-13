from fastapi import APIRouter, HTTPException, Query, Body, Depends, status
from backend.app.services.mongodb_service import MongoDBService
from backend.app.services.permission_service import PermissionService
from backend.app.models.project_management_models import (
    ListOwnedProjectsResponse,
    OwnedProjectItem,
    AddProjectMemberRequest,
    AddProjectMemberResponse,
    UpdateProjectMembersRequest,
    UpdateProjectMembersResponse,
    DeleteProjectRequest,
    DeleteProjectResponse
)
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger("project_management_api")

# --- Helpers ---

async def verify_user_is_owner(email: str, project_id: str, mongo_service: MongoDBService) -> bool:
    logger.info(f"[ProjectManagement] Verificando ownership: email={email}, project_id={project_id}")
    user = await mongo_service.get_user_by_email(email)
    company_id = getattr(user, "company_id", None)
    
    owner_projects = await mongo_service.get_projects_where_user_is_owner(email, company_id=company_id)
    is_owner = any(p["project_id"] == project_id for p in owner_projects)
    
    logger.info(f"[ProjectManagement] Ownership verificada: email={email}, project_id={project_id}, is_owner={is_owner}")
    return is_owner

# --- Routes ---

@router.get("/projects/owned", response_model=ListOwnedProjectsResponse, tags=["Project Management"])
async def list_owned_projects(email: str = Query(..., description="Email do usuário owner")):
    logger.info(f"[ProjectManagement] Recebida requisição para /projects/owned com email={email}")
    mongo_service = MongoDBService()
    
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

@router.post("/projects/{project_id}/members", response_model=AddProjectMemberResponse, tags=["Project Management"])
async def add_project_member(project_id: str, req: AddProjectMemberRequest = Body(...)):
    logger.info(f"[ProjectManagement] Adicionar membro: project_id={project_id}, requester={req.requester_email}")
    mongo_service = MongoDBService()
    permission_service = PermissionService(mongo_service)

    try:
        # 1. Validação de permissão via PermissionService
        has_perm, _, error_msg = await permission_service.check_user_project_action_permission(
            req.requester_email, project_id, action_type="add_member"
        )
        if not has_perm:
            return AddProjectMemberResponse(success=False, message=error_msg or "Sem permissão.")

        # 2. Validação extra de Ownership
        if not await verify_user_is_owner(req.requester_email, project_id, mongo_service):
            return AddProjectMemberResponse(success=False, message="Usuário não é owner deste projeto.")

        # 3. Busca novo membro
        new_user = await mongo_service.get_user_by_email(req.new_member_email)
        if not new_user:
            return AddProjectMemberResponse(success=False, message="Usuário a ser adicionado não encontrado.")

        new_member = {
            "user_id": str(new_user.id),
            "email": req.new_member_email,
            "role": req.role,
            "added_at": datetime.utcnow().isoformat()
        }

        result = await mongo_service.add_member_to_project(project_id, new_member)
        return AddProjectMemberResponse(success=bool(result), 
                                      message="Membro adicionado!" if result else "Erro ao adicionar.")
    except Exception as e:
        logger.error(f"Erro add_project_member: {e}")
        return AddProjectMemberResponse(success=False, message=str(e))

@router.put("/projects/{project_id}/members", response_model=UpdateProjectMembersResponse, tags=["Project Management"])
async def update_project_members(project_id: str, req: UpdateProjectMembersRequest = Body(...)):
    logger.info(f"[ProjectManagement] Atualizar membros: project_id={project_id}")
    mongo_service = MongoDBService()
    permission_service = PermissionService(mongo_service)

    try:
        has_perm, _, error_msg = await permission_service.check_user_project_action_permission(
            req.requester_email, project_id, action_type="edit"
        )
        if not has_perm:
            return UpdateProjectMembersResponse(success=False, message=error_msg)

        if not await verify_user_is_owner(req.requester_email, project_id, mongo_service):
            return UpdateProjectMembersResponse(success=False, message="Usuário não é owner.")

        result = await mongo_service.update_project_members(project_id, req.members)
        return UpdateProjectMembersResponse(success=bool(result), 
                                         message="Membros atualizados!" if result else "Falha na atualização.")
    except Exception as e:
        logger.error(f"Erro update_project_members: {e}")
        return UpdateProjectMembersResponse(success=False, message=str(e))

@router.delete("/projects/{project_id}", response_model=DeleteProjectResponse, tags=["Project Management"])
async def delete_project(project_id: str, req: DeleteProjectRequest = Body(...)):
    """
    Remove permanentemente um projeto do banco de dados.
    Exige que o solicitante tenha permissão de 'delete_project'.
    """
    logger.info(f"[ProjectManagement] Tentativa de exclusão: project_id={project_id}, por={req.requester_email}")
    mongo_service = MongoDBService()
    permission_service = PermissionService(mongo_service)

    try:
        # 1. Validação de permissão
        has_permission, _, error_msg = await permission_service.check_user_project_action_permission(
            req.requester_email, project_id, action_type="delete_project"
        )
        
        if not has_permission:
            logger.warning(f"[ProjectManagement] Acesso negado para exclusão: {req.requester_email}")
            raise HTTPException(status_code=403, detail=error_msg or "Permissão negada.")

        # 2. Execução da exclusão no MongoDB
        # Nota: Acessando a coleção diretamente via mongo_service.db
        result = await mongo_service.db.projects.delete_one({"project_id": project_id})

        if result.deleted_count == 1:
            logger.info(f"[ProjectManagement] Projeto {project_id} excluído com sucesso.")
            return DeleteProjectResponse(success=True, message="Projeto excluído com sucesso.")
        
        return DeleteProjectResponse(success=False, message="Projeto não encontrado ou já excluído.")

    except HTTPException as hex:
        raise hex
    except Exception as e:
        logger.error(f"[ProjectManagement] Erro crítico na exclusão: {e}")
        return DeleteProjectResponse(success=False, message=f"Erro interno: {str(e)}")
