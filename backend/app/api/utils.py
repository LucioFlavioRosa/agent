from fastapi import HTTPException
from typing import Tuple
from backend.app.services.mongodb_service import MongoDBService
from backend.app.models.permission_models import UserPermission

async def get_user_and_company_id(email: str, mongo_service: MongoDBService) -> Tuple[UserPermission, str]:
    user = await mongo_service.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    company_id = getattr(user, "company_id", None)
    if not company_id:
        raise HTTPException(status_code=400, detail="Usuário não possui company_id.")
    return user, company_id
