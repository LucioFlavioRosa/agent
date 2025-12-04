import json
import datetime
from typing import Optional, Dict, Any, List
from backend.app.core.config import settings
from backend.app.services.blob_storage_service import _get_blob_clients
import logging

class ProjectStateService:
    @staticmethod
    async def save_state_to_blob(session_data) -> str:
        state = session_data.to_project_state()
        usuario_executor = state.get("usuario_executor")
        projeto = state.get("projeto")
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        blob_folder = f"{usuario_executor}/{projeto}/estados"
        blob_filename = f"estado_{timestamp}.json"
        blob_path = f"{blob_folder}/{blob_filename}"
        _, container_client = _get_blob_clients()
        blob_client = container_client.get_blob_client(blob_path)
        if hasattr(session_data, "last_mcp_job_id"):
            state["last_mcp_job_id"] = getattr(session_data, "last_mcp_job_id")
        try:
            from backend.app.services.redis_session_service import RedisSessionService
            redis_service = RedisSessionService()
            session_id = getattr(session_data, "session_id", None)
            if session_id:
                session_redis = redis_service.get_session(session_id)
                reports_redis = getattr(session_redis, "reports", None)
                if reports_redis != state.get("reports"):
                    logging.error(f"Validação de consistência falhou: reports do estado não correspondem ao Redis para session_id={session_id}. Reports Redis: {reports_redis} | Reports estado: {state.get('reports')}")
                    raise Exception("O campo 'reports' do estado não corresponde ao valor atual no Redis. Abortando persistência.")
        except Exception as e:
            logging.error(f"Erro na validação de consistência antes de salvar estado no Blob: {e}")
            raise
        blob_client.upload_blob(json.dumps(state, ensure_ascii=False, separators=(',', ':')).encode("utf-8"), overwrite=True, content_settings=None)
        return blob_client.url

    @staticmethod
    async def load_latest_state_from_blob(usuario_executor: str, projeto: str) -> Optional[Dict[str, Any]]:
        logger = logging.getLogger("ProjectStateService")
        logger.info(f"Buscando estado para usuario_executor={usuario_executor}, projeto={projeto}")
        blob_folder = f"{usuario_executor}/{projeto}/estados"
        _, container_client = _get_blob_clients()
        blobs = list(container_client.list_blobs(name_starts_with=blob_folder+"/"))
        if not blobs:
            logger.info(f"Nenhum estado encontrado para usuario_executor={usuario_executor}, projeto={projeto}")
            return None
        blobs_sorted = sorted(
            [b for b in blobs if b.name.endswith(".json")],
            key=lambda b: b.name,
            reverse=True
        )
        if not blobs_sorted:
            logger.info(f"Nenhum arquivo .json de estado encontrado para usuario_executor={usuario_executor}, projeto={projeto}")
            return None
        latest_blob = blobs_sorted[0]
        blob_client = container_client.get_blob_client(latest_blob.name)
        state_bytes = blob_client.download_blob().readall()
        state = json.loads(state_bytes.decode("utf-8"))
        if "last_mcp_job_id" in state:
            state["last_mcp_job_id"] = state["last_mcp_job_id"]
        logger.info(f"Estado carregado com sucesso para usuario_executor={usuario_executor}, projeto={projeto}")
        return state

    @staticmethod
    async def get_latest_analysis_metadata(usuario_executor: str, projeto: str) -> Dict[str, str]:
        state = await ProjectStateService.load_latest_state_from_blob(usuario_executor, projeto)
        if not state:
            return {}
        analysis_type = state.get("analysis_type")
        return {
            "analysis_type": analysis_type
        }

    @staticmethod
    async def list_user_projects(usuario_executor: str) -> List[Dict[str, Any]]:
        logger = logging.getLogger("ProjectStateService")
        projects = {}
        try:
            _, container_client = _get_blob_clients()
            prefix = f"{usuario_executor}/"
            blobs = list(container_client.list_blobs(name_starts_with=prefix))
            for blob in blobs:
                parts = blob.name.split('/')
                if len(parts) >= 4 and parts[2] == 'estados' and blob.name.endswith('.json'):
                    projeto = parts[1]
                    if projeto not in projects:
                        projects[projeto] = []
                    projects[projeto].append(blob)
            result = []
            for projeto, blob_list in projects.items():
                blob_list_sorted = sorted(blob_list, key=lambda b: b.name, reverse=True)
                latest_blob = blob_list_sorted[0]
                blob_client = container_client.get_blob_client(latest_blob.name)
                state_bytes = blob_client.download_blob().readall()
                state = json.loads(state_bytes.decode("utf-8"))
                item = {
                    "projeto": state.get("projeto", projeto),
                    "analysis_type": state.get("analysis_type"),
                    "created_at": state.get("created_at"),
                    "last_saved_to_blob": state.get("last_saved_to_blob"),
                    "project_id": state.get("project_id")
                }
                result.append(item)
            return result
        except Exception as e:
            logger.error(f"Erro ao listar projetos do usuário {usuario_executor}: {e}")
            return []

    @staticmethod
    def _sanitize_project_list(projects: list) -> list:
        sanitized = []
        for p in projects:
            if isinstance(p, dict):
                p = dict(p)
                p.pop("analysis_name", None)
                if "project_id" not in p or not p["project_id"]:
                    continue
                sanitized.append(p)
        return sanitized

    @staticmethod
    async def _fetch_and_sanitize_projects(usuario_executor: str) -> list:
        logger = logging.getLogger("ProjectStateService")
        try:
            projects = await ProjectStateService.list_user_projects(usuario_executor)
            sanitized = ProjectStateService._sanitize_project_list(projects)
            return sanitized
        except Exception as e:
            logger.error(f"Erro ao buscar projetos do usuário {usuario_executor}: {e}")
            return []
