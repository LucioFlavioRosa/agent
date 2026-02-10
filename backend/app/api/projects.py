import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from backend.app.middleware.auth_middleware import get_current_user, _extract_usuario_executor
from backend.app.services.redis_session_service import RedisSessionService

router = APIRouter()
logger = logging.getLogger("projects_api")

@router.get("/check", tags=["Projects"])
async def check_project(
    nome_projeto: str = Query(..., description="Nome do projeto a ser verificado"),
    current_user: dict = Depends(get_current_user)
):
    redis_service = RedisSessionService()
    usuario_executor = _extract_usuario_executor(current_user)
    project_id = redis_service.get_project_id_by_nome_projeto(usuario_executor, nome_projeto)
    if project_id:
        return {"exists": True, "project_id": project_id}
    return {"exists": False}

@router.get("/list", tags=["Projects"])
async def list_projects(current_user: dict = Depends(get_current_user)):
    redis_service = RedisSessionService()
    usuario_executor = _extract_usuario_executor(current_user)
    projetos = redis_service.list_projects(usuario_executor)
    return projetos
