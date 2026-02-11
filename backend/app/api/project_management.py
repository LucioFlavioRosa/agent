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

router = APIRouter()

@router.get("/projects/owned", response_model=ListOwnedProjectsResponse, tags=["Project Management"])
async def list_owned_projects(email: str = Query(..., description="Email do usuário owner")):
    mongo_service = MongoDBService()
    projects = await mongo_service.get_projects_where_user_is_owner(email)
    items = [OwnedProjectItem(
        project_id=p["project_id"],
        name=p["name"],
        description=p.get("description"),
        members=p.get("members", [])
    ) for p in projects]
    return ListOwnedProjectsResponse(projects=items)

@router.post("/projects/{project_id}/members", response_model=AddProjectMemberResponse, tags=["Project Management"])
async def add_project_member(
    project_id: str,
    req: AddProjectMemberRequest = Body(...)
):
    mongo_service = MongoDBService()
    # Valida se requester é owner
    owner_projects = await mongo_service.get_projects_where_user_is_owner(req.requester_email)
    if not any(p["project_id"] == project_id for p in owner_projects):
        return AddProjectMemberResponse(success=False, message="Usuário não é owner deste projeto.")
    # Busca user_id do novo membro
    new_user = await mongo_service.get_user_by_email(req.new_member_email)
    if not new_user:
        return AddProjectMemberResponse(success=False, message="Usuário a ser adicionado não encontrado.")
    if req.role not in ["viewer", "editor"]:
        return AddProjectMemberResponse(success=False, message="Role inválida. Use viewer ou editor.")
    new_member = {
        "user_id": new_user.id,
        "email": req.new_member_email,
        "role": req.role,
        "added_at": datetime.utcnow().isoformat()
    }
    result = await mongo_service.add_member_to_project(project_id, new_member)
    if result:
        return AddProjectMemberResponse(success=True, message="Membro adicionado com sucesso.")
    else:
        return AddProjectMemberResponse(success=False, message="Falha ao adicionar membro ao projeto.")

@router.put("/projects/{project_id}/members", response_model=UpdateProjectMembersResponse, tags=["Project Management"])
async def update_project_members(
    project_id: str,
    req: UpdateProjectMembersRequest = Body(...)
):
    mongo_service = MongoDBService()
    # Valida se requester é owner
    owner_projects = await mongo_service.get_projects_where_user_is_owner(req.requester_email)
    if not any(p["project_id"] == project_id for p in owner_projects):
        return UpdateProjectMembersResponse(success=False, message="Usuário não é owner deste projeto.")
    # Salva membros
    result = await mongo_service.update_project_members(project_id, req.members)
    if result:
        return UpdateProjectMembersResponse(success=True, message="Membros do projeto atualizados com sucesso.")
    else:
        return UpdateProjectMembersResponse(success=False, message="Falha ao atualizar membros do projeto.")
