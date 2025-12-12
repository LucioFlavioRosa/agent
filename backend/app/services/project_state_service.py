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
    async def save_state_to_blob(state_data: Any) -> str:
        logger = logging.getLogger("ProjectStateService")
        if hasattr(state_data, "dict"):
            data = state_data.dict()
        elif hasattr(state_data, "model_dump"):
            data = state_data.model_dump()
        elif isinstance(state_data, dict):
            data = state_data
        else:
            data = state_data.__dict__
        usuario_executor = data.get("usuario_executor")
        nome_projeto = data.get("nome_projeto")
        if not usuario_executor or not nome_projeto:
            error_msg = f"Não é possível salvar estado: 'usuario_executor' ({usuario_executor}) ou 'nome_projeto' ({nome_projeto}) ausentes."
            logger.error(error_msg)
            raise ValueError(error_msg)
        subfolder_map = {
            "epicos_report": "epicos",
            "features_report": "features",
            "times_descricao_report": "times_descricao",
            "alocacao_times_report": "alocacao_times",
            "premissas_riscos_report": "premissas_riscos"
        }
        report_type = "resumo"
        subfolder = "resumo"
        for key, folder in subfolder_map.items():
            if key in data and data[key]:
                report_type = key
                subfolder = folder
                break
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        filename = f"estado_{report_type}_{timestamp}.json"
        blob_path = f"{usuario_executor}/{nome_projeto}/estados/{subfolder}/{filename}"
        try:
            _, container_client = _get_blob_clients()
            blob_client = container_client.get_blob_client(blob_path)
            json_data = json.dumps(data, default=str, ensure_ascii=False)
            logger.info(f"Iniciando upload de estado para: {blob_path}")
            blob_client.upload_blob(json_data, overwrite=True)
            logger.info(f"Upload concluído com sucesso: {blob_path}")
            return blob_client.url
        except Exception as e:
            logger.error(f"Erro ao salvar estado no blob: {str(e)}")
            raise e

    # ... demais métodos permanecem iguais ...
