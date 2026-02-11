from fastapi import APIRouter, Depends, Query
from backend.app.services.mongodb_service import MongoDBService
from backend.app.models.permission_models import ProjectPermission
from typing import List, Dict

router = APIRouter()

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
    user = await mongo_service.get_user_by_email(email)
    if not user:
        return []
    company_id = getattr(user, "company_id", None)
    if not company_id:
        return []
    # Busca todos os projetos onde o usuário é membro, filtrando por company_id
    projects_cursor = mongo_service.db.projects.find({"members.email": email, "company_id": company_id})
    projects = []
    async for doc in projects_cursor:
        try:
            project = ProjectPermission(**doc)
        except Exception:
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
    return projects
