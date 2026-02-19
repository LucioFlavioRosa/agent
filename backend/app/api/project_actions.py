from fastapi import APIRouter, Body, HTTPException, Depends 
from backend.app.models.project_action_models import ProjectActionRequest, ProjectActionResponse
from backend.app.services.permission_service import PermissionService
from backend.app.services.mongodb_service import MongoDBService
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.utils.logging_utils import log_request_received, log_response_sent
import logging

router = APIRouter()
logger = logging.getLogger("project_actions_api")

# --- Helper para Injeção de Dependência ---
def get_mongo_service():
    return MongoDBService()

def get_redis_service():
    return RedisSessionService()

@router.post("/{project_id}/actions/validate", response_model=ProjectActionResponse, tags=["Project Actions"])
async def validate_project_action(
    project_id: str,
    request: ProjectActionRequest = Body(...),
    mongo_service: MongoDBService = Depends(get_mongo_service),
    redis_service: RedisSessionService = Depends(get_redis_service)
):
    payload = {
        "email": request.email,
        "project_id": project_id,
        "action_type": request.action_type
    }
    
    # Atualizei os logs para refletir a nova URL limpa
    endpoint_str = f"/{project_id}/actions/validate"
    log_request_received(endpoint=endpoint_str, payload=payload)
    logger.info(f"[ProjectActions] Requisição recebida para validação de ação: {payload}")
    
    # 3. OTIMIZAÇÃO: Passamos o mongo_service existente para o PermissionService
    permission_service = PermissionService(mongo_service=mongo_service, redis_session_service=redis_service)
    
    allowed, role, error_msg = await permission_service.check_user_project_action_permission(
        request.email, project_id, request.action_type
    )
    
    response_obj = ProjectActionResponse(
        success=allowed,
        allowed=allowed,
        role=role,
        message=error_msg if error_msg else ("Ação permitida." if allowed else "Ação não permitida.")
    )
    
    log_response_sent(endpoint=endpoint_str, response=response_obj.dict(), job_id=None, project_id=project_id)
    logger.info(f"[ProjectActions] Resposta enviada: {response_obj.dict()}")
    
    if not allowed:
        raise HTTPException(status_code=403, detail=response_obj.message)
        
    return response_obj
