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
                resumo_states.append(state)
        projetos_resumo = []
        for state in resumo_states:
            resumo = {
                "nome_projeto": state.get("nome_projeto", ""),
                "ultima_analysis_type": state.get("ultima_analysis_type", ""),
                "created_at": state.get("created_at", None),
                "ultima_atualizacao": state.get("ultima_atualizacao", state.get("last_saved_to_blob", None)),
                "project_id": state.get("project_id")
            }
            projetos_resumo.append(resumo)
        logger.info(f"Projetos de resumo retornados para usuario_executor={usuario_executor}: {len(projetos_resumo)}")
        return projetos_resumo

    @staticmethod
    async def save_state_to_blob(session_data, report_type: Optional[str] = None) -> str:
        logger = logging.getLogger("ProjectStateService")
        usuario_executor = getattr(session_data, "usuario_executor", None)
        nome_projeto = getattr(session_data, "nome_projeto", None)
        project_id = getattr(session_data, "project_id", None)
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        last_update = datetime.datetime.utcnow()
        estados_base_folder = f"{usuario_executor}/{nome_projeto}/estados"
        campos_obrigatorios = {
            "usuario_executor": usuario_executor,
            "nome_projeto": nome_projeto,
            "project_id": project_id
        }
        campos_faltando = [campo for campo, valor in campos_obrigatorios.items() if not valor or (isinstance(valor, str) and not valor.strip())]
        if campos_faltando:
            logger.warning(f"Campos obrigatórios ausentes em session_data: {campos_faltando}. Tentando buscar estado do Blob Storage...")
            estado_blob = None
            try:
                estado_blob = await ProjectStateService.load_latest_state_from_blob(
                    usuario_executor or "",
                    project_id=project_id,
                    nome_projeto=nome_projeto
                )
            except Exception as e:
                logger.error(f"Erro ao buscar estado do Blob Storage para preencher campos obrigatórios: {str(e)}")
            if estado_blob:
                for campo in campos_faltando:
                    valor_blob = estado_blob.get(campo)
                    if valor_blob:
                        setattr(session_data, campo, valor_blob)
                        campos_obrigatorios[campo] = valor_blob
                campos_faltando = [campo for campo, valor in campos_obrigatorios.items() if not valor or (isinstance(valor, str) and not valor.strip())]
            if campos_faltando:
                raise ValueError(f"Não é possível salvar o estado: campos obrigatórios ausentes mesmo após fallback do Blob Storage: {campos_faltando}")
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
        usuario_executor = getattr(session_data, "usuario_executor", None)
        project_id = getattr(session_data, "project_id", None)
        ultima_analysis_type = getattr(session_data, "ultima_analysis_type", None) or getattr(session_data, "analysis_type", None)
        created_at = getattr(session_data, "created_at", None)
        if isinstance(created_at, str):
            created_at = datetime.datetime.fromisoformat(created_at)
        if not nome_projeto or not isinstance(nome_projeto, str) or not nome_projeto.strip():
            nome_projeto = getattr(session_data, 'nome_projeto', None) or 'PROJETO_SEM_NOME'
            if not nome_projeto or not isinstance(nome_projeto, str) or not nome_projeto.strip():
                raise ValueError("Campo 'nome_projeto' é obrigatório e não pode ser None ou vazio para criar o estado de resumo.")
        if not usuario_executor or not isinstance(usuario_executor, str) or not usuario_executor.strip():
            usuario_executor = getattr(session_data, 'usuario_executor', None) or 'USUARIO_SEM_NOME'
            if not usuario_executor or not isinstance(usuario_executor, str) or not usuario_executor.strip():
                raise ValueError("Campo 'usuario_executor' é obrigatório e não pode ser None ou vazio para criar o estado de resumo.")
        if not project_id or not isinstance(project_id, str) or not project_id.strip():
            project_id = getattr(session_data, 'project_id', None) or 'PROJECT_ID_SEM_NOME'
            if not project_id or not isinstance(project_id, str) or not project_id.strip():
                raise ValueError("Campo 'project_id' é obrigatório e não pode ser None ou vazio para criar o estado de resumo.")
        return EstadoResumoProjeto(
            nome_projeto=nome_projeto,
            ultima_analysis_type=ultima_analysis_type,
            created_at=created_at or datetime.datetime.utcnow(),
            ultima_atualizacao=last_update
        ).dict()

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
