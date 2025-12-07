import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from backend.app.middleware.auth_middleware import get_current_user, _extract_usuario_executor
from backend.app.services.project_state_service import ProjectStateService
from backend.app.models.project_models import ProjectListItem

router = APIRouter()
logger = logging.getLogger("projects_api")

@router.get("/check", tags=["Projects"])
async def check_project(
    nome_projeto: str = Query(..., description="Nome do projeto a ser verificado"),
    current_user: dict = Depends(get_current_user)
):
    usuario_executor = _extract_usuario_executor(current_user)
    logger.info(f"Verificando existência do projeto '{nome_projeto}' para usuario_executor='{usuario_executor}'")
    try:
        project_id = await ProjectStateService._get_project_id_by_name(usuario_executor, nome_projeto)
        if not project_id:
            logger.info(f"Projeto '{nome_projeto}' NÃO encontrado para usuario_executor='{usuario_executor}'.")
            return {"exists": False}
        state = await ProjectStateService.load_latest_state_from_blob(usuario_executor, project_id=project_id)
        if state:
            state.pop("projeto", None)
            state.pop("comentario_usuario", None)
            state.pop("docx_blob_url", None)
            state["project_id"] = project_id
            state["nome_projeto"] = state.get("nome_projeto", nome_projeto)
            response = {"exists": True, "state": state}
            return response
        else:
            logger.info(f"Projeto '{nome_projeto}' NÃO encontrado para usuario_executor='{usuario_executor}'.")
            return {"exists": False}
    except Exception as e:
        logger.error(f"Erro ao buscar estado do projeto '{nome_projeto}' para usuario_executor='{usuario_executor}': {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao buscar estado do projeto: {str(e)}")

@router.get("/list", response_model=List[ProjectListItem], tags=["Projects"])
async def list_projects(current_user: dict = Depends(get_current_user)):
    usuario_executor = _extract_usuario_executor(current_user)
    projects = await ProjectStateService._fetch_and_sanitize_projects(usuario_executor)
    for p in projects:
        if "nome_projeto" not in p:
            p["nome_projeto"] = p.get("nome_projeto", "")
        p.pop("projeto", None)
        p.pop("comentario_usuario", None)
        p.pop("docx_blob_url", None)
    return projects
