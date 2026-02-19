from fastapi import HTTPException
from typing import Tuple
import logging # <-- Importando logging

from backend.app.services.mongodb_service import MongoDBService
from backend.app.models.permission_models import UserPermission

logger = logging.getLogger("utils") # <-- Instanciando o logger

async def get_user_and_company_id(email: str, mongo_service: MongoDBService) -> Tuple[UserPermission, str]:
    user = await mongo_service.get_user_by_email(email)
    if not user:
        logger.warning(f"[Utils] Falha na validação: Usuário '{email}' não encontrado no banco.")
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    # Acesso direto e limpo (supondo que UserPermission tenha o campo company_id)
    company_id = user.company_id 
    
    if not company_id:
        logger.warning(f"[Utils] Falha na validação: Usuário '{email}' não possui company_id vinculado.")
        raise HTTPException(status_code=400, detail="Usuário não possui company_id.")
        
    return user, company_id
