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
import uuid
from backend.app.utils.project_id_validator import ensure_project_id, validate_and_fix_project_id

logger = logging.getLogger("ProjectStateService")

class ProjectStateService:
    _project_id_cache = {}

    @staticmethod
    def _normalize_nome_projeto(nome_projeto: Optional[str]) -> Optional[str]:
        if nome_projeto is None:
            return None
        return nome_projeto.strip().lower()

    @staticmethod
    def _get_val(data: Any, key: str, default: Any = None) -> Any:
        if isinstance(data, dict):
            return data.get(key, default)
        return getattr(data, key, default)

    @staticmethod
    def _set_val(data: Any, key: str, value: Any) -> None:
        if isinstance(data, dict):
            data[key] = value
        else:
            setattr(data, key, value)

    @staticmethod
    async def _fetch_and_sanitize_projects(usuario_executor: str) -> List[Dict[str, Any]]:
        logger = logging.getLogger("ProjectStateService")
        _, container_client = _get_blob_clients()
        prefix_resumo = f"{usuario_executor}/"
        blobs_resumo = list(container_client.list_blobs(name_starts_with=f"{prefix_resumo}"))
        resumo_states = []
        for blob in blobs_resumo:
            if blob.name.endswith('.json') and "estado_resumo_" in blob.name:
                blob_client = container_client.get_blob_client(blob.name)
                state_bytes = blob_client.download_blob().readall()
                state = json.loads(state_bytes.decode("utf-8"))
                nome_projeto = state.get("nome_projeto", "")
                project_id = state.get("project_id")
                if not project_id or not isinstance(project_id, str) or not project_id.strip():
                    project_id = validate_and_fix_project_id(state, usuario_executor, nome_projeto)
                    if not project_id or not isinstance(project_id, str) or not project_id.strip():
                        logger.warning(f"[SANITIZE] Estado de resumo ignorado por ausência de project_id: {blob.name}")
                        continue
                resumo = {
                    "nome_projeto": state.get("nome_projeto", ""),
                    "ultima_analysis_type": state.get("ultima_analysis_type", state.get("analysis_type", "")),
                    "created_at": state.get("created_at", None),
                    "last_saved_to_blob": state.get("ultima_atualizacao", state.get("last_saved_to_blob", None)),
                    "project_id": project_id
                }
                resumo_states.append(resumo)
        logger.info(f"Projetos de resumo retornados para usuario_executor={usuario_executor}: {len(resumo_states)}")
        projetos_unicos = {}
        for resumo in resumo_states:
            key = resumo.get("project_id") or ProjectStateService._normalize_nome_projeto(resumo.get("nome_projeto"))
            if not key:
                continue
            atualizacao = resumo.get("last_saved_to_blob") or resumo.get("created_at")
            try:
                atualizacao_dt = datetime.datetime.fromisoformat(atualizacao) if atualizacao else datetime.datetime.min
            except Exception:
                atualizacao_dt = datetime.datetime.min
            if key not in projetos_unicos or (
                projetos_unicos[key]["_atualizacao_dt"] < atualizacao_dt
            ):
                resumo["_atualizacao_dt"] = atualizacao_dt
                projetos_unicos[key] = resumo
        projetos_final = []
        for v in projetos_unicos.values():
            v.pop("_atualizacao_dt", None)
            if "analysis_type" in v:
                v.pop("analysis_type", None)
            projetos_final.append(v)
        logger.info(f"Projetos únicos e mais recentes retornados: {len(projetos_final)}")
        return projetos_final

    @staticmethod
    async def _get_project_id_by_name(usuario_executor: str, nome_projeto: str) -> Optional[str]:
        logger = logging.getLogger("ProjectStateService")
        nome_projeto_normalizado = ProjectStateService._normalize_nome_projeto(nome_projeto)
        cache_key = f"{usuario_executor}:{nome_projeto_normalizado}"
        if cache_key in ProjectStateService._project_id_cache:
            logger.debug(f"[CACHE] Retornando project_id do cache para usuario_executor={usuario_executor}, nome_projeto={nome_projeto_normalizado}: {ProjectStateService._project_id_cache[cache_key]}")
            return ProjectStateService._project_id_cache[cache_key]
        _, container_client = _get_blob_clients()
        prefix_resumo = f"{usuario_executor}/"
        blobs_resumo = list(container_client.list_blobs(name_starts_with=f"{prefix_resumo}"))
        for blob in blobs_resumo:
            if blob.name.endswith('.json') and "estado_resumo_" in blob.name:
                blob_client = container_client.get_blob_client(blob.name)
                state_bytes = blob_client.download_blob().readall()
                state = json.loads(state_bytes.decode("utf-8"))
                nome_blob = ProjectStateService._normalize_nome_projeto(state.get("nome_projeto", ""))
                project_id = state.get("project_id")
                if not project_id or not isinstance(project_id, str) or not project_id.strip():
                    project_id = validate_and_fix_project_id(state, usuario_executor, state.get("nome_projeto", ""))
                logger.debug(f"Verificando blob: {blob.name}, nome_projeto_blob={nome_blob}, project_id={project_id}")
                if nome_blob == nome_projeto_normalizado and project_id and isinstance(project_id, str) and project_id.strip():
                    ProjectStateService._project_id_cache[cache_key] = project_id
                    logger.info(f"Encontrado project_id={project_id} para nome_projeto={nome_projeto_normalizado}")
                    return project_id
        logger.warning(f"Nenhum project_id encontrado para usuario_executor={usuario_executor}, nome_projeto={nome_projeto_normalizado}")
        return None

    @staticmethod
    def _invalidate_project_id_cache(nome_projeto: str):
        nome_projeto_normalizado = ProjectStateService._normalize_nome_projeto(nome_projeto)
        keys_to_remove = [k for k in ProjectStateService._project_id_cache if k.endswith(f":{nome_projeto_normalizado}")]
        for k in keys_to_remove:
            del ProjectStateService._project_id_cache[k]

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
        logger.info(f"[DEBUG] Listando blobs com prefixo: {prefix}")
        blobs = list(container_client.list_blobs(name_starts_with=prefix))
        states = []
        for blob in blobs:
            if blob.name.endswith('.json') and file_prefix in blob.name:
                blob_client = container_client.get_blob_client(blob.name)
                state_bytes = blob_client.download_blob().readall()
                state = json.loads(state_bytes.decode("utf-8"))
                pid = state.get("project_id")
                if not pid or not isinstance(pid, str) or not pid.strip():
                    pid = validate_and_fix_project_id(state, usuario_executor, state.get("nome_projeto", ""))
                    if not pid or not isinstance(pid, str) or not pid.strip():
                        logger.warning(f"Estado ignorado por ausência de project_id: {blob.name}")
                        continue
                if project_id and pid == project_id:
                    logger.info(f"[DEBUG] Estado encontrado por project_id: {pid} no blob: {blob.name}")
                    return state
                if nome_projeto:
                    nome_blob = ProjectStateService._normalize_nome_projeto(state.get("nome_projeto", ""))
                    nome_projeto_normalizado = ProjectStateService._normalize_nome_projeto(nome_projeto)
                    if nome_blob == nome_projeto_normalizado:
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
            logger.info(f"[DEBUG] Estado mais recente encontrado para nome_projeto={nome_projeto}: {states_sorted[0][0].name}")
            return states_sorted[0][1]
        logger.info(f"Nenhum estado válido encontrado para usuario_executor={usuario_executor}, project_id={project_id}, nome_projeto={nome_projeto}, report_type={report_type}")
        return None

    @staticmethod
    async def load_all_states_from_blob(usuario_executor: str, project_id: str) -> Dict[str, Any]:
        logger.info(f"Carregando todos os estados para usuario={usuario_executor}, project_id={project_id}")
        _, container_client = _get_blob_clients()
        nome_projeto = None
        resumo_state = None
        prefix_resumo = f"{usuario_executor}/"
        blobs_resumo = list(container_client.list_blobs(name_starts_with=prefix_resumo))
        candidatos_resumo = []
        for blob in blobs_resumo:
            if blob.name.endswith('.json') and "estado_resumo_" in blob.name:
                blob_client = container_client.get_blob_client(blob.name)
                state_bytes = blob_client.download_blob().readall()
                state = json.loads(state_bytes.decode("utf-8"))
                pid = state.get("project_id")
                if not pid or not isinstance(pid, str) or not pid.strip():
                    pid = validate_and_fix_project_id(state, usuario_executor, state.get("nome_projeto", ""))
                    if not pid or not isinstance(pid, str) or not pid.strip():
                        logger.warning(f"[LOAD_ALL] Estado de resumo ignorado por ausência de project_id: {blob.name}")
                        continue
                if pid == project_id:
                    candidatos_resumo.append((blob, state))
        if candidatos_resumo:
            def get_sort_key(item):
                state = item[1]
                ts = state.get("ultima_atualizacao") or state.get("last_saved_to_blob")
                if ts:
                    try:
                        return datetime.datetime.fromisoformat(ts)
                    except Exception:
                        pass
                return datetime.datetime.min
            candidatos_resumo.sort(key=get_sort_key, reverse=True)
            resumo_state = candidatos_resumo[0][1]
            nome_projeto = resumo_state.get("nome_projeto")
        else:
            return {}
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
        if nome_projeto:
            for report_type in report_types:
                subfolder = subfolder_map[report_type]
                prefix = f"{usuario_executor}/{nome_projeto}/estados/{subfolder}/"
                file_prefix = f"estado_{report_type}_"
                blobs = list(container_client.list_blobs(name_starts_with=prefix))
                candidatos_report = []
                for blob in blobs:
                    if blob.name.endswith('.json') and file_prefix in blob.name:
                        blob_client = container_client.get_blob_client(blob.name)
                        state_bytes = blob_client.download_blob().readall()
                        state = json.loads(state_bytes.decode("utf-8"))
                        if state.get("project_id") == project_id:
                            candidatos_report.append((blob, state))
                if candidatos_report:
                    candidatos_report.sort(key=lambda item: datetime.datetime.fromisoformat(item[1].get("ultima_atualizacao", datetime.datetime.min.isoformat())), reverse=True)
                    latest_state = candidatos_report[0][1]
                    key_map = {
                        "epicos_report": "epicos",
                        "features_report": "features",
                        "times_descricao_report": "times_descricao",
                        "alocacao_times_report": "alocacao_times",
                        "premissas_riscos_report": "premissas_riscos"
                    }
                    states_dict[key_map[report_type]] = latest_state
        return EstadoCompletoProjetoResponse(**states_dict).dict()
