from fastapi import APIRouter, Depends, Query
from backend.app.services.mongodb_service import MongoDBService
from backend.app.models.permission_models import ProjectPermission
from typing import List, Dict
import logging

router = APIRouter()
logger = logging.getLogger("user_projects_api")

async def get_mongo_service():
    from backend.app.core.config import settings
    mongo_uri = getattr(settings, "MONGODB_URI", None)
    mongo_db_name = getattr(settings, "MONGODB_DATABASE_NAME", None)
    return MongoDBService(uri=mongo_uri, db_name=mongo_db_name)

@router.get("/projects", tags=["User Projects"])
async def get_user_projects(
    email: str = Query(..., description="Email do usuário"),
    empresa: str = Query(None, description="Empresa do usuário"),
    mongo_service: MongoDBService = Depends(get_mongo_service)
) -> List[Dict]:
    logger.info(f"[UserProjects] Recebida requisição para /projects com email='{email}', empresa='{empresa}'")
    user = await mongo_service.get_user_by_email(email)
    logger.info(f"[UserProjects] Resultado da busca de usuário no MongoDB para email='{email}': {'Encontrado' if user else 'Não encontrado'}")
    if not user:
        logger.warning(f"[UserProjects] Usuário '{email}' não encontrado. Retornando lista vazia.")
        return []
    company_id = getattr(user, "company_id", None)
    logger.info(f"[UserProjects] company_id do usuário '{email}': '{company_id}'")
    if not company_id:
        logger.warning(f"[UserProjects] Usuário '{email}' não possui company_id. Retornando lista vazia.")
        return []
    logger.info(f"[UserProjects] Buscando projetos do usuário '{email}' com company_id '{company_id}'")
    projects_cursor = mongo_service.db.projects.find({"members.email": email, "company_id": company_id})
    projects = []
    async for doc in projects_cursor:
        try:
            project = ProjectPermission(**doc)
            logger.debug(f"[UserProjects] Projeto encontrado: id='{project.id}', name='{project.name}'")
        except Exception as e:
            logger.error(f"[UserProjects] Erro ao construir ProjectPermission para doc id='{doc.get('_id')}', erro: {e}")
            continue
        member_role = None
        for member in project.members:
            if member.email == email:
                member_role = member.role
                break
        projects.append({
            "project_id": project.id,
            "name": project.name,
            "description": project.description,
            "role": member_role
        })
    logger.info(f"[UserProjects] Lista de projetos construída para usuário '{email}': {len(projects)} projetos encontrados.")
    logger.debug(f"[UserProjects] Conteúdo final da resposta: {projects}")
    return projects
