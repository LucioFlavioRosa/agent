from fastapi import APIRouter, Depends, Query
from backend.app.services.mongodb_service import MongoDBService
from backend.app.models.permission_models import ProjectPermission
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
    
    # 1. Busca o usuário no banco
    user = await mongo_service.get_user_by_email(email)
    
    if not user:
        logger.warning(f"[UserProjects] Usuário '{email}' não encontrado.")
        return []

    # 2. MELHORIA: Validação de Cruzamento (Email x Empresa)
    user_actual_company = getattr(user, "company_id", None) 

    if empresa and user_actual_company != empresa:
        logger.error(f"[UserProjects] Conflito de Segurança: Usuário {email} tentou acessar projetos da empresa {empresa}, mas pertence à {user_actual_company}")
        raise HTTPException(
            status_code=403, 
            detail="Você não tem permissão para acessar os dados desta empresa."
        )

    # 3. Filtro de busca robusto
    query = {
        "members.email": email, 
        "company_id": user_actual_company
    }
    
    projects_cursor = mongo_service.db.projects.find(query)
    projects = []

    async for doc in projects_cursor:
        try:
            project = ProjectPermission(**doc)
            
            # Identifica a role do usuário neste projeto específico
            member_role = next((m.role for m in project.members if m.email == email), None)
            
            projects.append({
                "project_id": project.id,
                "name": project.name,
                "description": project.description,
                "role": member_role
            })
        except Exception as e:
            logger.error(f"[UserProjects] Erro ao processar projeto {doc.get('_id')}: {e}")
            continue

    return projects
