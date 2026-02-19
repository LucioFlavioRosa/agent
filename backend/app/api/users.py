from fastapi import APIRouter, HTTPException, Body, Path, Depends, Request
from backend.app.services.mongodb_service import MongoDBService
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.models.permission_models import UserPermission
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
import logging

router = APIRouter()
logger = logging.getLogger("users_api")

async def get_mongo_service(request: Request) -> MongoDBService:
    return request.app.state.mongo_service

def get_redis_service() -> RedisSessionService:
    return RedisSessionService()

class CreateUserRequest(BaseModel):
    email: EmailStr
    name: str
    company_id: str
    active: Optional[bool] = True
    group_ids: Optional[List[str]] = []

class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    company_id: Optional[str] = None
    active: Optional[bool] = None
    group_ids: Optional[List[str]] = None

# --- Rota Refatorada ---
@router.post("/users", tags=["Users"])
async def create_user(
    request: CreateUserRequest = Body(...),
    mongo_service: MongoDBService = Depends(get_mongo_service), # Injetado!
    redis_service: RedisSessionService = Depends(get_redis_service) # Injetado!
):
    user_data = request.dict()
    
    try:
        # Verifica se usuário já existe
        existing = await mongo_service.db.users.find_one({"email": request.email})
        if existing:
            raise HTTPException(status_code=409, detail="Usuário já existe.")
            
        await mongo_service.db.users.insert_one(user_data)
        
        # Invalida cache do usuário
        await redis_service.invalidate_user_permissions(request.email, request.company_id)
        
        # Invalida cache de todos usuários dos grupos
        if request.group_ids:
            for group_id in request.group_ids:
                group_doc = await mongo_service.db.groups.find_one({"_id": group_id})
                if group_doc and group_doc.get("members"):
                    for member in group_doc["members"]:
                        await redis_service.invalidate_user_permissions(member["email"], group_doc["company_id"])
                        
        return {"success": True, "message": "Usuário criado com sucesso."}
        
    except HTTPException as http_exc:
        # Repassa o erro HTTP corretamente para o frontend (ex: o erro 409 de conflito)
        raise http_exc
    except Exception as e:
        logger.error(f"Erro ao criar usuário: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao criar usuário.")

@router.put("/users/{user_id}", tags=["Users"])
async def update_user(
    user_id: str = Path(..., description="ID do usuário a ser atualizado"),
    request: UpdateUserRequest = Body(...)
):
    mongo_service = MongoDBService()
    redis_service = RedisSessionService()
    try:
        user_doc = await mongo_service.db.users.find_one({"_id": user_id})
        if not user_doc:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        update_fields = {k: v for k, v in request.dict().items() if v is not None}
        await mongo_service.db.users.update_one({"_id": user_id}, {"$set": update_fields})
        # Invalida cache do usuário
        email = user_doc["email"]
        company_id = update_fields.get("company_id", user_doc["company_id"])
        await redis_service.invalidate_user_permissions(email, company_id)
        # Se group_ids foi modificado, invalida cache de todos usuários dos grupos afetados
        if "group_ids" in update_fields:
            for group_id in update_fields["group_ids"]:
                group_doc = await mongo_service.db.groups.find_one({"_id": group_id})
                if group_doc and group_doc.get("members"):
                    for member in group_doc["members"]:
                        await redis_service.invalidate_user_permissions(member["email"], group_doc["company_id"])
        return {"success": True, "message": "Usuário atualizado com sucesso."}
    except Exception as e:
        logger.error(f"Erro ao atualizar usuário: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/users/{user_id}", tags=["Users"])
async def delete_user(user_id: str = Path(..., description="ID do usuário a ser deletado")):
    mongo_service = MongoDBService()
    redis_service = RedisSessionService()
    try:
        user_doc = await mongo_service.db.users.find_one({"_id": user_id})
        if not user_doc:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        email = user_doc["email"]
        company_id = user_doc["company_id"]
        group_ids = user_doc.get("group_ids", [])
        await mongo_service.db.users.delete_one({"_id": user_id})
        # Invalida cache do usuário
        await redis_service.invalidate_user_permissions(email, company_id)
        # Invalida cache de todos usuários dos grupos afetados
        for group_id in group_ids:
            group_doc = await mongo_service.db.groups.find_one({"_id": group_id})
            if group_doc and group_doc.get("members"):
                for member in group_doc["members"]:
                    await redis_service.invalidate_user_permissions(member["email"], group_doc["company_id"])
        return {"success": True, "message": "Usuário deletado com sucesso."}
    except Exception as e:
        logger.error(f"Erro ao deletar usuário: {e}")
        raise HTTPException(status_code=500, detail=str(e))
