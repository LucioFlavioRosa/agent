from fastapi import APIRouter, Body, HTTPException
from backend.app.models.project_action_models import ProjectActionRequest, ProjectActionResponse
from backend.app.services.permission_service import PermissionService
from backend.app.utils.logging_utils import log_request_received, log_response_sent
import logging

router = APIRouter()
logger = logging.getLogger("project_actions_api")

@router.post("/projects/{project_id}/actions/validate", response_model=ProjectActionResponse, tags=["Project Actions"])
async def validate_project_action(
    project_id: str,
    request: ProjectActionRequest = Body(...)
):
    payload = {
        "email": request.email,
        "project_id": project_id,
        "action_type": request.action_type
    }
    log_request_received(endpoint=f"/projects/{project_id}/actions/validate", payload=payload)
    logger.info(f"[ProjectActions] Requisição recebida para validação de ação: {payload}")
    permission_service = PermissionService()
    allowed, role, error_msg = await permission_service.check_user_project_action_permission(
        request.email, project_id, request.action_type
    )
    response_obj = ProjectActionResponse(
        success=allowed,
        allowed=allowed,
        role=role,
        message=error_msg if error_msg else ("Ação permitida." if allowed else "Ação não permitida.")
    )
    log_response_sent(endpoint=f"/projects/{project_id}/actions/validate", response=response_obj.dict(), job_id=None, project_id=project_id)
    logger.info(f"[ProjectActions] Resposta enviada: {response_obj.dict()}")
    if not allowed:
        raise HTTPException(status_code=403, detail=response_obj.message)
    return response_obj
