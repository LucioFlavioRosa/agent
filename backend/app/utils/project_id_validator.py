import uuid
import logging
from backend.app.services.project_state_service import ProjectStateService
import asyncio

def ensure_project_id(session_data: dict, usuario_executor: str = None, nome_projeto: str = None) -> str:
    logger = logging.getLogger("project_id_validator")
    project_id = session_data.get("project_id")
    if project_id and isinstance(project_id, str) and project_id.strip():
        return project_id
    estado_blob = None
    try:
        if usuario_executor and nome_projeto:
            try:
                # Tenta buscar estado do blob storage (async)
                estado_blob = asyncio.run(ProjectStateService.load_latest_state_from_blob(usuario_executor, nome_projeto=nome_projeto))
            except Exception as e:
                logger.error(f"Erro ao buscar estado do Blob Storage para preencher project_id: {str(e)}")
        if estado_blob and estado_blob.get("project_id"):
            session_data["project_id"] = estado_blob["project_id"]
            return estado_blob["project_id"]
    except Exception as e:
        logger.error(f"Erro inesperado ao tentar garantir project_id: {str(e)}")
    novo_id = str(uuid.uuid4())
    session_data["project_id"] = novo_id
    logger.critical(f"project_id ausente, gerado novo UUID: {novo_id}")
    return novo_id
