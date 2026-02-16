from fastapi import APIRouter, Query, HTTPException, Depends, Request
from backend.app.services.mongodb_service import MongoDBService
from backend.app.services.permission_service import PermissionService
from backend.app.models.agent_access_models import UserAgentsListResponse, AgentAccessResponse
from backend.app.utils.logging_utils import log_request_received, log_response_sent
import logging
from typing import List

router = APIRouter()
logger = logging.getLogger("user_agents_api")

async def get_mongo_service(request: Request) -> MongoDBService:
    return request.app.state.mongo_service

@router.get("/agents", response_model=UserAgentsListResponse, tags=["User Agents"])
async def get_user_agents(
    email: str = Query(..., description="Email do usuário"),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    log_request_received(endpoint="/user/agents", payload={"email": email})
    logger.info(f"[UserAgents] Requisição recebida para /user/agents | Email: {email}")

    # 1. Valida usuário
    user = await mongo_service.get_user_by_email(email)
    if not user:
        logger.warning(f"[UserAgents] Usuário '{email}' não encontrado.")
        log_response_sent(endpoint="/user/agents", response={"detail": "Usuário não encontrado."})
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if not user.active:
        logger.warning(f"[UserAgents] Usuário '{email}' está inativo.")
        log_response_sent(endpoint="/user/agents", response={"detail": "Usuário inativo."})
        raise HTTPException(status_code=403, detail="Usuário inativo.")
    company_id = getattr(user, "company_id", None)
    if not company_id:
        logger.warning(f"[UserAgents] Usuário '{email}' não possui company_id.")
        log_response_sent(endpoint="/user/agents", response={"detail": "Usuário não possui company_id."})
        raise HTTPException(status_code=400, detail="Usuário não possui company_id.")

    # 2. Busca agentes permitidos
    permission_service = PermissionService(mongo_service)
    allowed_agents, error_msg = await permission_service.get_user_allowed_agents(email)
    if error_msg:
        logger.warning(f"[UserAgents] Erro ao buscar agentes: {error_msg}")
        log_response_sent(endpoint="/user/agents", response={"detail": error_msg})
        raise HTTPException(status_code=400, detail=error_msg)

    # 3. Monta resposta
    agents_response: List[AgentAccessResponse] = [AgentAccessResponse(agent_name=agent) for agent in allowed_agents]
    response_obj = UserAgentsListResponse(agents=agents_response)
    log_response_sent(endpoint="/user/agents", response=response_obj.dict())
    return response_obj
