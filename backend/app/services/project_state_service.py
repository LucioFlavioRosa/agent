import json
import datetime
from typing import Optional, Dict, Any, List
from backend.app.core.config import settings
from backend.app.services.blob_storage_service import _get_blob_clients
import logging
from backend.app.models.project_state_models import (
    EstadoResumoProjeto,
    EstadoEpicos,
    EstadoFeatures,
    EstadoTimesDescricao,
    EstadoAlocacaoTimes,
    EstadoPremissasRiscos,
    EstadoCompletoProjetoResponse
)
from backend.app.config.analysis_type_to_report_mapping import analysis_type_to_report_mapping

class ProjectStateService:
    _project_id_cache = {}

    @staticmethod
    async def save_state_to_blob(session_data, report_type: Optional[str] = None) -> str:
        usuario_executor = getattr(session_data, "usuario_executor", None)
        nome_projeto = getattr(session_data, "nome_projeto", None)
        project_id = getattr(session_data, "project_id", None)
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        last_update = datetime.datetime.utcnow()
        estados_base_folder = f"{usuario_executor}/{nome_projeto}/estados"
        if report_type:
            subfolder_map = {
                "epicos_report": "epicos",
                "features_report": "features",
                "times_descricao_report": "times_descricao",
                "alocacao_times_report": "alocacao_times",
                "premissas_riscos_report": "premissas_riscos"
            }
            subfolder = subfolder_map.get(report_type)
            if not subfolder:
                raise ValueError(f"Report type desconhecido: {report_type}")
            blob_folder = f"{estados_base_folder}/{subfolder}"
            blob_filename = f"estado_{report_type}_{timestamp}.json"
            state = ProjectStateService._build_report_state(session_data, report_type, last_update)
        else:
            blob_folder = f"{estados_base_folder}/resumo"
            blob_filename = f"estado_resumo_{timestamp}.json"
            state = ProjectStateService._build_resumo_state(session_data, last_update)
        blob_path = f"{blob_folder}/{blob_filename}"
        _, container_client = _get_blob_clients()
        blob_client = container_client.get_blob_client(blob_path)
        blob_client.upload_blob(json.dumps(state, ensure_ascii=False, separators=(',', ':')).encode("utf-8"), overwrite=True, content_settings=None)
        ProjectStateService._invalidate_project_id_cache(nome_projeto)
        return blob_client.url

    @staticmethod
    def _build_resumo_state(session_data, last_update):
        nome_projeto = getattr(session_data, "nome_projeto", None)
        ultima_analysis_type = getattr(session_data, "ultima_analysis_type", None) or getattr(session_data, "analysis_type", None)
        created_at = getattr(session_data, "created_at", None)
        if isinstance(created_at, str):
            created_at = datetime.datetime.fromisoformat(created_at)
        return EstadoResumoProjeto(
            nome_projeto=nome_projeto,
            ultima_analysis_type=ultima_analysis_type,
            created_at=created_at or datetime.datetime.utcnow(),
            ultima_atualizacao=last_update
        ).dict()

    @staticmethod
    def _build_report_state(session_data, report_type, last_update):
        nome_projeto = getattr(session_data, "nome_projeto", None)
        ultima_analysis_type = getattr(session_data, "ultima_analysis_type", None) or getattr(session_data, "analysis_type", None)
        created_at = getattr(session_data, "created_at", None)
        if isinstance(created_at, str):
            created_at = datetime.datetime.fromisoformat(created_at)
        report_data = getattr(session_data, report_type, [])
        if report_type == "epicos_report":
            return EstadoEpicos(
                nome_projeto=nome_projeto,
                ultima_analysis_type=ultima_analysis_type,
                created_at=created_at or datetime.datetime.utcnow(),
                ultima_atualizacao=last_update,
                epicos_report=report_data
            ).dict()
        elif report_type == "features_report":
            return EstadoFeatures(
                nome_projeto=nome_projeto,
                ultima_analysis_type=ultima_analysis_type,
                created_at=created_at or datetime.datetime.utcnow(),
                ultima_atualizacao=last_update,
                features_report=report_data
            ).dict()
        elif report_type == "times_descricao_report":
            return EstadoTimesDescricao(
                nome_projeto=nome_projeto,
                ultima_analysis_type=ultima_analysis_type,
                created_at=created_at or datetime.datetime.utcnow(),
                ultima_atualizacao=last_update,
                times_descricao_report=report_data
            ).dict()
        elif report_type == "alocacao_times_report":
            return EstadoAlocacaoTimes(
                nome_projeto=nome_projeto,
                ultima_analysis_type=ultima_analysis_type,
                created_at=created_at or datetime.datetime.utcnow(),
                ultima_atualizacao=last_update,
                alocacao_times_report=report_data
            ).dict()
        elif report_type == "premissas_riscos_report":
            return EstadoPremissasRiscos(
                nome_projeto=nome_projeto,
                ultima_analysis_type=ultima_analysis_type,
                created_at=created_at or datetime.datetime.utcnow(),
                ultima_atualizacao=last_update,
                premissas_riscos_report=report_data
            ).dict()
        else:
            raise ValueError(f"Report type desconhecido: {report_type}")

    @staticmethod
    async def load_latest_state_from_blob(usuario_executor: str, project_id: Optional[str] = None, nome_projeto: Optional[str] = None, report_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        logger = logging.getLogger("ProjectStateService")
        _, container_client = _get_blob_clients()
        estados_base_folder = f"{usuario_executor}/"
        if report_type:
            subfolder_map = {
                "epicos_report": "epicos",
                "features_report": "features",
                "times_descricao_report": "times_descricao",
                "alocacao_times_report": "alocacao_times",
                "premissas_riscos_report": "premissas_riscos"
            }
            subfolder = subfolder_map.get(report_type)
            if not subfolder:
                return None
            prefix = f"{estados_base_folder}{nome_projeto}/estados/{subfolder}/"
            file_prefix = f"estado_{report_type}_"
        else:
            prefix = f"{estados_base_folder}{nome_projeto}/estados/resumo/"
            file_prefix = "estado_resumo_"
        blobs = list(container_client.list_blobs(name_starts_with=prefix))
        states = []
        for blob in blobs:
            if blob.name.endswith('.json') and file_prefix in blob.name:
                blob_client = container_client.get_blob_client(blob.name)
                state_bytes = blob_client.download_blob().readall()
                state = json.loads(state_bytes.decode("utf-8"))
                if project_id and state.get("project_id") == project_id:
                    return state
                if nome_projeto and state.get("nome_projeto") == nome_projeto:
                    states.append((blob, state))
        if nome_projeto and states:
            def get_sort_key(item):
                state = item[1]
                ts = state.get("ultima_atualizacao") or state.get("last_saved_to_blob")
                if ts:
                    try:
                        return datetime.datetime.fromisoformat(ts)
                    except Exception:
                        pass
                return datetime.datetime.min
            states_sorted = sorted(states, key=get_sort_key, reverse=True)
            return states_sorted[0][1]
        logger.info(f"Nenhum estado encontrado para usuario_executor={usuario_executor}, project_id={project_id}, nome_projeto={nome_projeto}, report_type={report_type}")
        return None

    @staticmethod
    async def load_all_states_from_blob(usuario_executor: str, project_id: str) -> Dict[str, Any]:
        _, container_client = _get_blob_clients()
        # Buscar nome_projeto pelo project_id no estado resumo
        nome_projeto = None
        resumo_state = None
        prefix_resumo = f"{usuario_executor}/"
        blobs_resumo = list(container_client.list_blobs(name_starts_with=f"{prefix_resumo}"))
        resumo_states = []
        for blob in blobs_resumo:
            if blob.name.endswith('.json') and "estado_resumo_" in blob.name:
                blob_client = container_client.get_blob_client(blob.name)
                state_bytes = blob_client.download_blob().readall()
                state = json.loads(state_bytes.decode("utf-8"))
                if state.get("project_id") == project_id:
                    resumo_states.append((blob, state))
        if resumo_states:
            def get_sort_key(item):
                state = item[1]
                ts = state.get("ultima_atualizacao") or state.get("last_saved_to_blob")
                if ts:
                    try:
                        return datetime.datetime.fromisoformat(ts)
                    except Exception:
                        pass
                return datetime.datetime.min
            resumo_states_sorted = sorted(resumo_states, key=get_sort_key, reverse=True)
            resumo_state = resumo_states_sorted[0][1]
            nome_projeto = resumo_state.get("nome_projeto")
        else:
            return {}
        # Buscar cada report
        report_types = [
            "epicos_report",
            "features_report",
            "times_descricao_report",
            "alocacao_times_report",
            "premissas_riscos_report"
        ]
        subfolder_map = {
            "epicos_report": "epicos",
            "features_report": "features",
            "times_descricao_report": "times_descricao",
            "alocacao_times_report": "alocacao_times",
            "premissas_riscos_report": "premissas_riscos"
        }
        states_dict = {
            "resumo": resumo_state,
            "epicos": None,
            "features": None,
            "times_descricao": None,
            "alocacao_times": None,
            "premissas_riscos": None
        }
        for report_type in report_types:
            subfolder = subfolder_map[report_type]
            prefix = f"{usuario_executor}/{nome_projeto}/estados/{subfolder}/"
            file_prefix = f"estado_{report_type}_"
            blobs = list(container_client.list_blobs(name_starts_with=prefix))
            states = []
            for blob in blobs:
                if blob.name.endswith('.json') and file_prefix in blob.name:
                    blob_client = container_client.get_blob_client(blob.name)
                    state_bytes = blob_client.download_blob().readall()
                    state = json.loads(state_bytes.decode("utf-8"))
                    if state.get("project_id") == project_id:
                        states.append((blob, state))
            if states:
                states_sorted = sorted(states, key=lambda item: datetime.datetime.fromisoformat(item[1].get("ultima_atualizacao", datetime.datetime.min.isoformat())), reverse=True)
                latest_state = states_sorted[0][1]
                if report_type == "epicos_report":
                    states_dict["epicos"] = latest_state
                elif report_type == "features_report":
                    states_dict["features"] = latest_state
                elif report_type == "times_descricao_report":
                    states_dict["times_descricao"] = latest_state
                elif report_type == "alocacao_times_report":
                    states_dict["alocacao_times"] = latest_state
                elif report_type == "premissas_riscos_report":
                    states_dict["premissas_riscos"] = latest_state
        return EstadoCompletoProjetoResponse(**states_dict).dict()

    @staticmethod
    async def _get_project_id_by_name(usuario_executor: str, nome_projeto: str) -> Optional[str]:
        cache_key = f"{usuario_executor}:{nome_projeto}"
        if cache_key in ProjectStateService._project_id_cache:
            return ProjectStateService._project_id_cache[cache_key]
        state = await ProjectStateService.load_latest_state_from_blob(usuario_executor, project_id=None, nome_projeto=nome_projeto)
        if state and state.get("project_id"):
            project_id = state.get("project_id")
            ProjectStateService._project_id_cache[cache_key] = project_id
            return project_id
        return None

    @staticmethod
    def _invalidate_project_id_cache(nome_projeto: str):
        keys_to_remove = [k for k in ProjectStateService._project_id_cache if k.endswith(f":{nome_projeto}")]
        for k in keys_to_remove:
            del ProjectStateService._project_id_cache[k]

    @staticmethod
    async def get_report_state(project_id: str, report_type: str) -> Optional[Dict[str, Any]]:
        from backend.app.services.redis_session_service import RedisSessionService
        redis_service = RedisSessionService()
        state = redis_service.get_report_state(project_id, report_type)
        if state:
            return state
        usuario_executor = None
        nome_projeto = None
        resumo_state = redis_service.get_resumo_state(project_id)
        if resumo_state:
            usuario_executor = resumo_state.get("usuario_executor")
            nome_projeto = resumo_state.get("nome_projeto")
        if usuario_executor and nome_projeto:
            blob_state = await ProjectStateService.load_latest_state_from_blob(usuario_executor, project_id=project_id, nome_projeto=nome_projeto, report_type=report_type)
            if blob_state:
                return blob_state
        return None
