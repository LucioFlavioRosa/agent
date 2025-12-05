import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from backend.app.middleware.auth_middleware import get_current_user, _extract_usuario_executor
from backend.app.services.project_state_service import ProjectStateService
from backend.app.models.project_models import ProjectListItem
from backend.app.services.redis_session_service import RedisSessionService

router = APIRouter()
logger = logging.getLogger("projects_api")

@router.get("/check", tags=["Projects"])
async def check_project(
    projeto: str = Query(..., description="Nome do projeto a ser verificado"),
    current_user: dict = Depends(get_current_user)
):
    usuario_executor = _extract_usuario_executor(current_user)
    logger.info(f"Verificando existência do projeto '{projeto}' para usuario_executor='{usuario_executor}'")
    try:
        redis_service = RedisSessionService()
        session = redis_service.get_session_by_project(usuario_executor, projeto)
        if session:
            session_id = session.session_id
            state = await ProjectStateService.load_latest_state_from_redis(session_id)
            if state:
                state.pop("analysis_name", None)
                logger.info(f"Projeto '{projeto}' encontrado no Redis para usuario_executor='{usuario_executor}'. Estado retornado.")
                return {"exists": True, "state": state}
        state = await ProjectStateService.load_latest_state_from_blob(usuario_executor, projeto)
        if state:
            state.pop("analysis_name", None)
            session_id_blob = state.get("session_id")
            if session_id_blob:
                try:
                    redis_service.restore_session_from_state(
                        usuario_executor,
                        projeto,
                        state.get("analysis_type"),
                        state,
                        session_id=session_id_blob
                    )
                    logger.info(f"Sessão restaurada do Blob para usuario_executor='{usuario_executor}', projeto='{projeto}', session_id='{session_id_blob}'")
                except Exception as e:
                    logger.warning(f"Falha ao restaurar sessão do Blob: {e}")
            logger.info(f"Projeto '{projeto}' encontrado no Blob Storage para usuario_executor='{usuario_executor}'. Estado retornado.")
            return {"exists": True, "state": state}
        else:
            logger.info(f"Projeto '{projeto}' NÃO encontrado para usuario_executor='{usuario_executor}'.")
            return {"exists": False}
    except Exception as e:
        logger.error(f"Erro ao buscar estado do projeto '{projeto}' para usuario_executor='{usuario_executor}': {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao buscar estado do projeto: {str(e)}")

@router.get("/list", response_model=List[ProjectListItem], tags=["Projects"])
async def list_projects(current_user: dict = Depends(get_current_user)):
    usuario_executor = _extract_usuario_executor(current_user)
    projects = await ProjectStateService._fetch_and_sanitize_projects(usuario_executor)
    return projects
