from fastapi import APIRouter, Depends, Query, HTTPException, Request
from backend.app.services.mongodb_service import MongoDBService
from typing import List, Dict
import logging

router = APIRouter()
logger = logging.getLogger("user_projects_api")

async def get_mongo_service(request: Request) -> MongoDBService:
    return request.app.state.mongo_service

@router.get("/projects", tags=["User Projects"])
async def get_user_projects(
    email: str = Query(..., description="Email do usuário"),
    empresa: str = Query(None, description="Nome ou ID da empresa enviado pelo Front"),
    mongo_service: MongoDBService = Depends(get_mongo_service)
) -> List[Dict]:
    logger.info(f"[UserProjects] Requisição para /projects | Email: {email} | Empresa solicitada: {empresa}")
    
    # 1. Busca o usuário no banco para validação de segurança (Contexto da Requisição)
    user = await mongo_service.get_user_by_email(email)
    
    if not user:
        logger.warning(f"[UserProjects] Usuário '{email}' não encontrado.")
        return []

    # 2. Validação de Cruzamento (Email x Empresa)
    # Mantemos essa lógica aqui pois é específica de controle de acesso da API
    user_actual_company = getattr(user, "company_id", None) 

    if empresa and user_actual_company != empresa:
        logger.error(f"[UserProjects] Conflito de Segurança: Usuário {email} tentou acessar projetos da empresa {empresa}, mas pertence à {user_actual_company}")
        raise HTTPException(
            status_code=403, 
            detail="Você não tem permissão para acessar os dados desta empresa."
        )

    # 3. Busca de Projetos via Service (Refatorado)
    try:
        service_projects = await mongo_service.get_user_projects_with_access(email)
        
        # 4. Mapeamento para o formato esperado pelo Front
        # O service retorna 'project_name', mas o contrato original da API retornava 'name'.
        response = [
            {
                "project_id": p["project_id"],
                "name": p["project_name"],  # Mapeia project_name -> name
                "description": p["description"],
                "role": p["role"]
            }
            for p in service_projects
        ]
        
        return response

    except Exception as e:
        logger.error(f"[UserProjects] Erro ao buscar projetos via service: {e}")
        return []
