from fastapi import APIRouter, HTTPException, Query, Body
from backend.app.services.mongodb_service import MongoDBService
from backend.app.models.project_management_models import (
    ListOwnedProjectsResponse,
    OwnedProjectItem,
    AddProjectMemberRequest,
    AddProjectMemberResponse,
    UpdateProjectMembersRequest,
    UpdateProjectMembersResponse
)
from backend.app.models.permission_models import ProjectMember
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger("project_management_api")

async def verify_user_is_owner(email: str, project_id: str, mongo_service: MongoDBService) -> bool:
    logger.info(f"[ProjectManagement] Verificando ownership: email={email}, project_id={project_id}")
    owner_projects = await mongo_service.get_projects_where_user_is_owner(email, company_id=getattr(await mongo_service.get_user_by_email(email), "company_id", None))
    is_owner = any(p["project_id"] == project_id for p in owner_projects)
    logger.info(f"[ProjectManagement] Ownership verificada: email={email}, project_id={project_id}, is_owner={is_owner}")
    return is_owner

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
    logger.info(f"[ProjectManagement] Buscando projetos onde usuário é owner: email={email}, company_id={company_id}")
    projects = await mongo_service.get_projects_where_user_is_owner(email, company_id=company_id)
    items = [OwnedProjectItem(
        project_id=p["project_id"],
        name=p["name"],
        description=p.get("description"),
        members=p.get("members", [])
    ) for p in projects]
    logger.info(f"[ProjectManagement] Projetos encontrados para email={email}: count={len(items)}")
    response = ListOwnedProjectsResponse(projects=items)
    logger.info(f"[ProjectManagement] Resposta final enviada para /projects/owned, email={email}, projetos={len(items)}")
    return response

@router.post("/projects/{project_id}/members", response_model=AddProjectMemberResponse, tags=["Project Management"])
async def add_project_member(
    project_id: str,
    req: AddProjectMemberRequest = Body(...)
):
    logger.info(f"[ProjectManagement] Recebida requisição para adicionar membro: project_id={project_id}, requester_email={req.requester_email}, new_member_email={req.new_member_email}, role={req.role}")
    mongo_service = MongoDBService()
    user = await mongo_service.get_user_by_email(req.requester_email)
    if not user:
        logger.error(f"[ProjectManagement] Usuário solicitante não encontrado: {req.requester_email}")
        return AddProjectMemberResponse(success=False, message="Usuário solicitante não encontrado.")
    company_id = getattr(user, "company_id", None)
    if not company_id:
        logger.error(f"[ProjectManagement] Usuário solicitante não possui company_id: {req.requester_email}")
        return AddProjectMemberResponse(success=False, message="Usuário solicitante não possui company_id.")
    if not await verify_user_is_owner(req.requester_email, project_id, mongo_service):
        logger.error(f"[ProjectManagement] Usuário não é owner do projeto: {req.requester_email}, project_id={project_id}")
        return AddProjectMemberResponse(success=False, message="Usuário não é owner deste projeto.")
    # Busca user_id do novo membro
    new_user = await mongo_service.get_user_by_email(req.new_member_email)
    if not new_user:
        logger.error(f"[ProjectManagement] Usuário a ser adicionado não encontrado: {req.new_member_email}")
        return AddProjectMemberResponse(success=False, message="Usuário a ser adicionado não encontrado.")
    if req.role not in ["viewer", "editor"]:
        logger.error(f"[ProjectManagement] Role inválida: {req.role}")
        return AddProjectMemberResponse(success=False, message="Role inválida. Use viewer ou editor.")
    new_member = {
        "user_id": new_user.id,
        "email": req.new_member_email,
        "role": req.role,
        "added_at": datetime.utcnow().isoformat()
    }
    logger.info(f"[ProjectManagement] Adicionando novo membro ao projeto: project_id={project_id}, new_member_email={req.new_member_email}, role={req.role}")
    result = await mongo_service.add_member_to_project(project_id, new_member)
    if result:
        logger.info(f"[ProjectManagement] Membro adicionado com sucesso: project_id={project_id}, new_member_email={req.new_member_email}")
        return AddProjectMemberResponse(success=True, message="Membro adicionado com sucesso.")
    else:
        logger.error(f"[ProjectManagement] Falha ao adicionar membro ao projeto: project_id={project_id}, new_member_email={req.new_member_email}")
        return AddProjectMemberResponse(success=False, message="Falha ao adicionar membro ao projeto.")

@router.put("/projects/{project_id}/members", response_model=UpdateProjectMembersResponse, tags=["Project Management"])
async def update_project_members(
    project_id: str,
    req: UpdateProjectMembersRequest = Body(...)
):
    logger.info(f"[ProjectManagement] Recebida requisição para atualizar membros: project_id={project_id}, requester_email={req.requester_email}, members_count={len(req.members)}")
    mongo_service = MongoDBService()
    user = await mongo_service.get_user_by_email(req.requester_email)
    if not user:
        logger.error(f"[ProjectManagement] Usuário solicitante não encontrado: {req.requester_email}")
        return UpdateProjectMembersResponse(success=False, message="Usuário solicitante não encontrado.")
    company_id = getattr(user, "company_id", None)
    if not company_id:
        logger.error(f"[ProjectManagement] Usuário solicitante não possui company_id: {req.requester_email}")
        return UpdateProjectMembersResponse(success=False, message="Usuário solicitante não possui company_id.")
    if not await verify_user_is_owner(req.requester_email, project_id, mongo_service):
        logger.error(f"[ProjectManagement] Usuário não é owner do projeto: {req.requester_email}, project_id={project_id}")
        return UpdateProjectMembersResponse(success=False, message="Usuário não é owner deste projeto.")
    logger.info(f"[ProjectManagement] Atualizando membros do projeto: project_id={project_id}, members_count={len(req.members)}")
    result = await mongo_service.update_project_members(project_id, req.members)
    if result:
        logger.info(f"[ProjectManagement] Membros do projeto atualizados com sucesso: project_id={project_id}, members_count={len(req.members)}")
        return UpdateProjectMembersResponse(success=True, message="Membros do projeto atualizados com sucesso.")
    else:
        logger.error(f"[ProjectManagement] Falha ao atualizar membros do projeto: project_id={project_id}")
        return UpdateProjectMembersResponse(success=False, message="Falha ao atualizar membros do projeto.")
