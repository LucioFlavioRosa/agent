import json
import datetime
from typing import Optional, Dict, Any, List
from backend.app.core.config import settings
from backend.app.services.blob_storage_service import _get_blob_clients
import logging

REPORT_FIELDS = [
    "epicos_report",
    "features_report",
    "times_descricao_report",
    "alocacao_times_report",
    "premissas_riscos_report"
]

class ProjectStateService:
    @staticmethod
    async def save_state_to_blob(session_data) -> str:
        state = session_data.to_project_state()
        usuario_executor = state.get("usuario_executor")
        projeto = state.get("projeto")
        session_id = state.get("session_id")
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        blob_folder = f"{usuario_executor}/{projeto}/estados"
        blob_filename = f"estado_{session_id}_{timestamp}.json"
        blob_path = f"{blob_folder}/{blob_filename}"
        _, container_client = _get_blob_clients()
        blob_client = container_client.get_blob_client(blob_path)
        logger = logging.getLogger("ProjectStateService")
        for k in REPORT_FIELDS:
            if k not in state:
                logger.critical(f"[save_state_to_blob] Campo de relatório '{k}' ausente, preenchendo com None.")
                state[k] = None
        logger.info(f"[save_state_to_blob] Conteúdo dos campos de relatório antes de salvar:")
        for k in REPORT_FIELDS:
            logger.info(f"[save_state_to_blob] {k}: {json.dumps(state.get(k, None), ensure_ascii=False)}")
        blob_client.upload_blob(json.dumps(state, ensure_ascii=False, separators=(',', ':')).encode("utf-8"), overwrite=True, content_settings=None)
        logger.info(f"[save_state_to_blob] Persistência concluída no Blob Storage: {blob_path}")
        return blob_client.url

    @staticmethod
    async def load_latest_state_from_blob(usuario_executor: str, projeto: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        logger = logging.getLogger("ProjectStateService")
        logger.info(f"Buscando estado para usuario_executor={usuario_executor}, projeto={projeto}, session_id={session_id}")
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
        if session_id:
            blobs_sorted = [b for b in blobs_sorted if f"_{session_id}_" in b.name]
        if not blobs_sorted:
            logger.info(f"Nenhum arquivo .json de estado encontrado para usuario_executor={usuario_executor}, projeto={projeto}, session_id={session_id}")
            return None
        latest_blob = blobs_sorted[0]
        blob_client = container_client.get_blob_client(latest_blob.name)
        state_bytes = blob_client.download_blob().readall()
        state = json.loads(state_bytes.decode("utf-8"))
        logger.info(f"Estado carregado com sucesso para usuario_executor={usuario_executor}, projeto={projeto}, session_id={session_id}")
        reports_dict = state.get('reports')
        if reports_dict and (
            'epicos_report' not in state and
            'features_report' not in state and
            'times_descricao_report' not in state and
            'alocacao_times_report' not in state and
            'premissas_riscos_report' not in state
        ):
            state['epicos_report'] = reports_dict.get('epicos_report') or reports_dict.get('epicos')
            state['features_report'] = reports_dict.get('features_report') or reports_dict.get('features')
            state['times_descricao_report'] = reports_dict.get('times_descricao_report') or reports_dict.get('times_descricao')
            state['alocacao_times_report'] = reports_dict.get('alocacao_times_report') or reports_dict.get('alocacao_times')
            state['premissas_riscos_report'] = reports_dict.get('premissas_riscos_report') or reports_dict.get('premissas_riscos')
            logger.info(f"[load_latest_state_from_blob] Migrado campo 'reports' para campos individuais de relatório.")
        for k in REPORT_FIELDS:
            if k not in state:
                logger.warning(f"[load_latest_state_from_blob] Campo de relatório '{k}' ausente, preenchendo com None.")
                state[k] = None
        logger.info(f"[load_latest_state_from_blob] Conteúdo dos campos de relatório após carregar do Blob:")
        for k in REPORT_FIELDS:
            logger.info(f"[load_latest_state_from_blob] {k}: {json.dumps(state.get(k, None), ensure_ascii=False)}")
        return state

    @staticmethod
    async def load_latest_state_from_redis(session_id: str) -> Optional[Dict[str, Any]]:
        from backend.app.services.redis_session_service import RedisSessionService
        logger = logging.getLogger("ProjectStateService")
        try:
            redis_service = RedisSessionService()
            session = redis_service.get_session(session_id)
            if session:
                return session.to_project_state()
        except Exception as e:
            logger.error(f"Erro ao buscar estado do Redis para session_id={session_id}: {e}")
        return None

    @staticmethod
    async def get_latest_analysis_metadata(usuario_executor: str, projeto: str, session_id: Optional[str] = None) -> Dict[str, str]:
        state = await ProjectStateService.load_latest_state_from_blob(usuario_executor, projeto, session_id=session_id)
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
                    "project_id": state.get("project_id"),
                    "session_id": state.get("session_id")
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

    @staticmethod
    async def load_latest_state_by_session_id(session_id: str) -> Optional[Dict[str, Any]]:
        logger = logging.getLogger("ProjectStateService")
        logger.info(f"[load_latest_state_by_session_id] Buscando estado mais recente no Blob Storage para session_id={session_id}")
        _, container_client = _get_blob_clients()
        blobs = list(container_client.list_blobs())
        matching_blobs = [b for b in blobs if b.name.endswith('.json') and f"_{session_id}_" in b.name]
        if not matching_blobs:
            logger.info(f"[load_latest_state_by_session_id] Nenhum arquivo de estado encontrado para session_id={session_id}")
            return None
        matching_blobs_sorted = sorted(matching_blobs, key=lambda b: b.name, reverse=True)
        latest_blob = matching_blobs_sorted[0]
        blob_client = container_client.get_blob_client(latest_blob.name)
        state_bytes = blob_client.download_blob().readall()
        state = json.loads(state_bytes.decode("utf-8"))
        logger.info(f"[load_latest_state_by_session_id] Estado carregado com sucesso para session_id={session_id}")
        for k in REPORT_FIELDS:
            if k not in state:
                logger.warning(f"[load_latest_state_by_session_id] Campo de relatório '{k}' ausente, preenchendo com None.")
                state[k] = None
        return state

    @staticmethod
    async def get_session_id_from_latest_state(usuario_executor: str, projeto: str) -> Optional[str]:
        from backend.app.services.redis_session_service import RedisSessionService
        logger = logging.getLogger("ProjectStateService")
        try:
            redis_service = RedisSessionService()
            session = redis_service.get_session_by_project(usuario_executor, projeto)
            if session:
                return session.session_id
        except Exception as e:
            logger.warning(f"get_session_id_from_latest_state: Sessão não encontrada no Redis para usuario_executor={usuario_executor}, projeto={projeto}: {e}")
        try:
            state = await ProjectStateService.load_latest_state_from_blob(usuario_executor, projeto)
            if state and state.get("session_id"):
                return state.get("session_id")
        except Exception as e:
            logger.warning(f"get_session_id_from_latest_state: Estado não encontrado no Blob para usuario_executor={usuario_executor}, projeto={projeto}: {e}")
        return None
