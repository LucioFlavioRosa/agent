from fastapi import APIRouter, HTTPException, Query, Path, Depends, Body
from backend.app.services.mongodb_service import MongoDBService
from backend.app.utils.logging_utils import log_request_received, log_response_sent
from backend.app.services.redis_session_service import RedisSessionService
import logging
from typing import List, Optional

router = APIRouter()
logger = logging.getLogger("groups_api")

async def get_mongo_service(request):
    return request.app.state.mongo_service

@router.get("/groups/{group_id}", tags=["Groups"])
async def get_group_by_id(
    group_id: str = Path(..., description="ID do grupo a ser consultado"),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    log_request_received(endpoint=f"/groups/{group_id}", payload={"group_id": group_id})
    logger.info(f"[Groups] Requisição recebida para /groups/{{group_id}}: group_id={group_id}")
    try:
        group = await mongo_service.get_group_by_id(group_id)
        if not group:
            logger.warning(f"[Groups] Grupo não encontrado: group_id={group_id}")
            raise HTTPException(status_code=404, detail="Grupo não encontrado.")
        response = group.dict() if hasattr(group, 'dict') else group
        log_response_sent(endpoint=f"/groups/{group_id}", response=response)
        return response
    except HTTPException as exc:
        log_response_sent(endpoint=f"/groups/{group_id}", response={"detail": exc.detail})
        raise
    except Exception as e:
        logger.error(f"[Groups] Erro ao buscar grupo: {e}")
        log_response_sent(endpoint=f"/groups/{group_id}", response={"detail": str(e)})
        raise HTTPException(status_code=500, detail="Erro interno ao buscar grupo.")

@router.get("/groups", tags=["Groups"])
async def list_groups(
    company_id: Optional[str] = Query(None, description="ID da empresa para listar todos os grupos (Modo Admin)"),
    email: Optional[str] = Query(None, description="Email para listar apenas os grupos do usuário (Modo Dropdown)"),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    log_request_received(endpoint="/groups", payload={"company_id": company_id, "email": email})
    logger.info(f"[Groups] Requisição recebida para /groups: company_id={company_id}, email={email}")
    
    if not company_id and not email:
        logger.warning("[Groups] Nenhum parâmetro de filtro fornecido.")
        raise HTTPException(status_code=400, detail="É obrigatório informar 'company_id' ou 'email'.")
        
    try:
        # ==========================================
        # CENÁRIO 1: O Frontend pediu os grupos do usuário (Dropdown do Novo Projeto)
        # ==========================================
        if email:
            user = await mongo_service.get_user_by_email(email)
            if not user:
                raise HTTPException(status_code=404, detail="Usuário não encontrado.")
            
            # Extrai os IDs dos grupos de forma segura (lidando com objeto ou dicionário)
            group_ids = getattr(user, "group_ids", user.get("group_ids", []) if isinstance(user, dict) else [])
            
            if not group_ids:
                return {"groups": []} # Retorna vazio se o usuário não tiver especialidades
                
            # Busca os detalhes apenas dos grupos permitidos
            groups_cursor = mongo_service.db.groups.find({"_id": {"$in": group_ids}})
            groups = await groups_cursor.to_list(length=100)
            
            # Formata exatamente como o Frontend está esperando (array de id e name)
            response_data = [{"id": str(g["_id"]), "name": g.get("name", "Grupo Sem Nome")} for g in groups]
            
            log_response_sent(endpoint="/groups", response={"user_groups": len(response_data)})
            return {"groups": response_data}

        # ==========================================
        # CENÁRIO 2: Lógica Original (Modo Admin)
        # ==========================================
        elif company_id:
            groups = await mongo_service.list_groups_by_company(company_id)
            response = [g.dict() if hasattr(g, 'dict') else g for g in groups]
            log_response_sent(endpoint="/groups", response=response)
            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Groups] Erro ao listar grupos: {e}")
        log_response_sent(endpoint="/groups", response={"detail": str(e)})
        raise HTTPException(status_code=500, detail="Erro interno ao listar grupos.")

@router.post("/groups", tags=["Groups"])
async def create_group(
    group_data: dict = Body(...),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    log_request_received(endpoint="/groups", payload=group_data)
    logger.info(f"[Groups] Requisição recebida para criação de grupo: {group_data}")
    group_id = await mongo_service.create_group(group_data)
    if not group_id:
        logger.error(f"[Groups] Falha ao criar grupo.")
        raise HTTPException(status_code=500, detail="Falha ao criar grupo.")
    # Cache invalidation: todos usuários do grupo
    users_cursor = mongo_service.db.users.find({"group_ids": group_id})
    async for user_doc in users_cursor:
        email = user_doc.get("email")
        company_id = user_doc.get("company_id")
        if email and company_id:
            await RedisSessionService().invalidate_user_permissions(email, company_id)
    log_response_sent(endpoint="/groups", response={"group_id": group_id})
    return {"group_id": group_id}

@router.put("/groups/{group_id}", tags=["Groups"])
async def update_group(
    group_id: str = Path(..., description="ID do grupo a ser atualizado"),
    group_data: dict = Body(...),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    log_request_received(endpoint=f"/groups/{group_id}", payload=group_data)
    logger.info(f"[Groups] Requisição recebida para atualização de grupo: group_id={group_id}, data={group_data}")
    success = await mongo_service.update_group(group_id, group_data)
    if not success:
        logger.error(f"[Groups] Falha ao atualizar grupo.")
        raise HTTPException(status_code=500, detail="Falha ao atualizar grupo.")
    # Cache invalidation: todos usuários do grupo
    users_cursor = mongo_service.db.users.find({"group_ids": group_id})
    async for user_doc in users_cursor:
        email = user_doc.get("email")
        company_id = user_doc.get("company_id")
        if email and company_id:
            await RedisSessionService().invalidate_user_permissions(email, company_id)
    log_response_sent(endpoint=f"/groups/{group_id}", response={"success": True})
    return {"success": True}

@router.delete("/groups/{group_id}", tags=["Groups"])
async def delete_group(
    group_id: str = Path(..., description="ID do grupo a ser deletado"),
    mongo_service: MongoDBService = Depends(get_mongo_service)
):
    log_request_received(endpoint=f"/groups/{group_id}", payload={"group_id": group_id})
    logger.info(f"[Groups] Requisição recebida para exclusão de grupo: group_id={group_id}")
    success = await mongo_service.delete_group(group_id)
    if not success:
        logger.error(f"[Groups] Falha ao excluir grupo.")
        raise HTTPException(status_code=500, detail="Falha ao excluir grupo.")
    # Cache invalidation: todos usuários do grupo
    users_cursor = mongo_service.db.users.find({"group_ids": group_id})
    async for user_doc in users_cursor:
        email = user_doc.get("email")
        company_id = user_doc.get("company_id")
        if email and company_id:
            await RedisSessionService().invalidate_user_permissions(email, company_id)
    log_response_sent(endpoint=f"/groups/{group_id}", response={"success": True})
    return {"success": True}
