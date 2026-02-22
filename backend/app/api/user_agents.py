from fastapi import APIRouter, Query, HTTPException, status, Depends
from backend.app.services.mongodb_service import MongoDBService
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.models.user_agents_models import UserAgentsResponse
import logging
from typing import List

router = APIRouter()
logger = logging.getLogger("user_agents_api")

async def get_mongo_service(request):
    return request.app.state.mongo_service

@router.get("/agents", response_model=UserAgentsResponse, tags=["User Agents"])
async def get_user_agents(
    email: str = Query(..., description="Email do usuário"),
    empresa: str = Query(..., description="Empresa do usuário (ID ou nome)"),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    logger.info(f"[UserAgents] Consulta de agentes para email={email}, empresa={empresa}")
    try:
        # 1. Valida usuário
        user = await mongo_service.get_user_by_email(email)
        if not user:
            logger.warning(f"[UserAgents] Usuário '{email}' não encontrado.")
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        user_company_id = getattr(user, "company_id", None)
        if not user_company_id:
            logger.warning(f"[UserAgents] Usuário '{email}' não possui company_id.")
            raise HTTPException(status_code=400, detail="Usuário não possui company_id.")
        if empresa != user_company_id:
            logger.error(f"[UserAgents] Conflito de empresa: usuário pertence à '{user_company_id}', mas foi solicitado '{empresa}'.")
            raise HTTPException(status_code=403, detail="Você não tem permissão para acessar os dados desta empresa.")

        # 2. Busca no Redis
        redis_service = RedisSessionService()
        permissions = await redis_service.get_user_permissions(email, user_company_id)
        if permissions and permissions.get("allowed_agents") is not None:
            allowed_agents = permissions.get("allowed_agents", [])
            logger.info(f"[UserAgents] Cache hit: agentes encontrados no Redis para {email}:{user_company_id}: {allowed_agents}")
            return UserAgentsResponse(allowed_agents=allowed_agents)

        # 3. Cache miss: busca grupos do usuário
        group_ids = getattr(user, "group_ids", [])
        allowed_agents_set = set()
        if group_ids:
            for group_id in group_ids:
                agents = await mongo_service.get_group_allowed_agents(group_id)
                allowed_agents_set.update(agents)
        allowed_agents = sorted(list(allowed_agents_set))

        # 4. Armazena no Redis com tipagem Pydantic
        from datetime import datetime
        from backend.app.models.permission_models import UserPermissionCache

        permissions_cache = UserPermissionCache(
            email=email,
            company_id=user_company_id,
            allowed_agents=allowed_agents,
            project_permissions={},
            cached_at=datetime.utcnow().isoformat()
        )
        
        await redis_service.store_user_permissions(email, user_company_id, permissions_cache.dict())
        logger.info(f"[UserAgents] Cache atualizado no Redis para {email}:{user_company_id} com agentes: {allowed_agents}")

        return UserAgentsResponse(allowed_agents=allowed_agents)
    except HTTPException as exc:
        logger.error(f"[UserAgents] Erro: {exc.detail}")
        raise
    except Exception as e:
        logger.error(f"[UserAgents] Erro interno: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao consultar agentes do usuário.")
