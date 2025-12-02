import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from backend.app.middleware.auth_middleware import get_current_user
from backend.app.services.project_state_service import ProjectStateService
from backend.app.models.project_models import ProjectListItem

router = APIRouter()
logger = logging.getLogger("projects_api")

@router.get("/check", tags=["Projects"])
async def check_project(
    projeto: str = Query(..., description="Nome do projeto a ser verificado"),
    current_user: dict = Depends(get_current_user)
):
    usuario_executor = current_user.get("usuario_executor") or current_user.get("sub")
    logger.info(f"Verificando existência do projeto '{projeto}' para usuario_executor='{usuario_executor}'")
    try:
        state = await ProjectStateService.load_latest_state_from_blob(usuario_executor, projeto)
        if state:
            logger.info(f"Projeto '{projeto}' encontrado para usuario_executor='{usuario_executor}'. Estado retornado.")
            return {"exists": True, "state": state}
        else:
            logger.info(f"Projeto '{projeto}' NÃO encontrado para usuario_executor='{usuario_executor}'.")
            return {"exists": False}
    except Exception as e:
        logger.error(f"Erro ao buscar estado do projeto '{projeto}' para usuario_executor='{usuario_executor}': {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao buscar estado do projeto: {str(e)}")

@router.get("/list", response_model=List[ProjectListItem], tags=["Projects"])
async def list_projects(current_user: dict = Depends(get_current_user)):
    usuario_executor = current_user.get("usuario_executor") or current_user.get("sub")
    try:
        projects = await ProjectStateService.list_user_projects(usuario_executor)
        return projects
    except Exception as e:
        logger.error(f"Erro ao listar projetos do usuário {usuario_executor}: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar lista de projetos.")
