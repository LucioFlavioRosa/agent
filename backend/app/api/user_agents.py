from fastapi import APIRouter, Query, Depends, HTTPException
from backend.app.services.mongodb_service import MongoDBService
from backend.app.services.permission_service import PermissionService
from backend.app.models.user_agents_models import UserAgentsResponse
from typing import List
import logging

router = APIRouter()
logger = logging.getLogger("user_agents_api")

async def get_mongo_service(request):
    return request.app.state.mongo_service

@router.get("/agents", response_model=UserAgentsResponse, tags=["User Agents"])
async def get_user_agents(
    email: str = Query(..., description="Email do usuário"),
    empresa: str = Query(..., description="Empresa do usuário"),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    logger.info(f"[UserAgents] Consulta de agentes para email={email}, empresa={empresa}")
    if not email or not empresa:
        logger.warning(f"[UserAgents] Parâmetros obrigatórios ausentes: email={email}, empresa={empresa}")
        raise HTTPException(status_code=400, detail="Parâmetros obrigatórios: email e empresa.")

    # Busca usuário no MongoDB
    user = await mongo_service.get_user_by_email(email)
    if not user:
        logger.warning(f"[UserAgents] Usuário '{email}' não encontrado.")
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    user_company_id = getattr(user, "company_id", None)
    if not user_company_id:
        logger.warning(f"[UserAgents] Usuário '{email}' não possui company_id.")
        raise HTTPException(status_code=400, detail="Usuário não possui company_id.")
    if empresa != user_company_id:
        logger.error(f"[UserAgents] Conflito de empresa: '{empresa}' != '{user_company_id}' para usuário '{email}'")
        raise HTTPException(status_code=403, detail="Você não tem permissão para acessar os dados desta empresa.")

    permission_service = PermissionService(mongo_service)
    allowed_agents: List[str] = await permission_service.get_user_allowed_agents(email, user_company_id)
    return UserAgentsResponse(allowed_agents=allowed_agents)
