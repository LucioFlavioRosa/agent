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
from backend.app.utils.project_id_validator import ensure_project_id

logger = logging.getLogger("ProjectStateService")

class ProjectStateService:
    _project_id_cache = {}

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
                    # Tenta garantir project_id
                    project_id = ensure_project_id(state, usuario_executor, nome_projeto)
                    if not project_id or not isinstance(project_id, str) or not project_id.strip():
                        logger.warning(f"Estado de resumo ignorado por ausência de project_id: {blob.name}")
                        continue
                resumo = {
                    "nome_projeto": state.get("nome_projeto", ""),
                    "ultima_analysis_type": state.get("ultima_analysis_type", ""),
                    "created_at": state.get("created_at", None),
                    "ultima_atualizacao": state.get("ultima_atualizacao", state.get("last_saved_to_blob", None)),
                    "project_id": project_id
                }
                resumo_states.append(resumo)
        logger.info(f"Projetos de resumo retornados para usuario_executor={usuario_executor}: {len(resumo_states)}")
        return resumo_states

    @staticmethod
    async def save_state_to_blob(session_data, report_type: Optional[str] = None) -> str:
        logger = logging.getLogger("ProjectStateService")
        usuario_executor = ProjectStateService._get_val(session_data, "usuario_executor")
        nome_projeto = ProjectStateService._get_val(session_data, "nome_projeto")
        # project_id garantido via utilitário
        project_id = ensure_project_id(session_data, usuario_executor, nome_projeto)
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
                        ProjectStateService._set_val(session_data, campo, valor_blob)
                        campos_obrigatorios[campo] = valor_blob
                campos_faltando = [campo for campo, valor in campos_obrigatorios.items() if not valor or (isinstance(valor, str) and not valor.strip())]
            if campos_faltando:
                logger.critical(f"Não é possível salvar o estado: campos obrigatórios ausentes mesmo após fallback do Blob Storage: {campos_faltando}")
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
        def json_serial(obj):
            if isinstance(obj, (datetime.datetime, datetime.date)):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
        blob_client.upload_blob(
            json.dumps(
                state, 
                default=json_serial, 
                ensure_ascii=False, 
                separators=(',', ':')
            ).encode("utf-8"), 
            overwrite=True, 
            content_settings=None
        )
        ProjectStateService._invalidate_project_id_cache(nome_projeto)
        return blob_client.url

    @staticmethod
    def _build_resumo_state(session_data, last_update):
        nome_projeto = ProjectStateService._get_val(session_data, "nome_projeto")
        usuario_executor = ProjectStateService._get_val(session_data, "usuario_executor")
        # project_id garantido via utilitário
        project_id = ensure_project_id(session_data, usuario_executor, nome_projeto)
        ultima_analysis_type = ProjectStateService._get_val(session_data, "ultima_analysis_type") or ProjectStateService._get_val(session_data, "analysis_type")
        created_at = ProjectStateService._get_val(session_data, "created_at")
        if isinstance(created_at, str):
            created_at = datetime.datetime.fromisoformat(created_at)
        if not nome_projeto or not isinstance(nome_projeto, str) or not nome_projeto.strip():
            nome_projeto = ProjectStateService._get_val(session_data, 'nome_projeto') or 'PROJETO_SEM_NOME'
            if not nome_projeto or not isinstance(nome_projeto, str) or not nome_projeto.strip():
                raise ValueError("Campo 'nome_projeto' é obrigatório e não pode ser None ou vazio para criar o estado de resumo.")
        if not usuario_executor or not isinstance(usuario_executor, str) or not usuario_executor.strip():
            usuario_executor = ProjectStateService._get_val(session_data, 'usuario_executor') or 'USUARIO_SEM_NOME'
            if not usuario_executor or not isinstance(usuario_executor, str) or not usuario_executor.strip():
                raise ValueError("Campo 'usuario_executor' é obrigatório e não pode ser None ou vazio para criar o estado de resumo.")
        if not project_id or not isinstance(project_id, str) or not project_id.strip():
            project_id = ensure_project_id(session_data, usuario_executor, nome_projeto)
            if not project_id or not isinstance(project_id, str) or not project_id.strip():
                logger.critical("project_id ausente mesmo após tentativa de geração/recuperação no _build_resumo_state")
                raise ValueError("Campo 'project_id' é obrigatório e não pode ser None ou vazio para criar o estado de resumo.")
        resumo = EstadoResumoProjeto(
            nome_projeto=nome_projeto,
            ultima_analysis_type=ultima_analysis_type,
            created_at=created_at or datetime.datetime.utcnow(),
            ultima_atualizacao=last_update
        ).dict()
        resumo["project_id"] = project_id
        resumo["usuario_executor"] = usuario_executor
        return resumo

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
                pid = state.get("project_id")
                if not pid or not isinstance(pid, str) or not pid.strip():
                    # Tenta garantir project_id
                    nome_proj = state.get("nome_projeto")
                    pid = ensure_project_id(state, usuario_executor, nome_proj)
                    if not pid or not isinstance(pid, str) or not pid.strip():
                        logger.warning(f"Estado ignorado por ausência de project_id: {blob.name}")
                        continue
                if project_id and pid == project_id:
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
        logger.info(f"Nenhum estado válido encontrado para usuario_executor={usuario_executor}, project_id={project_id}, nome_projeto={nome_projeto}, report_type={report_type}")
        return None

    @staticmethod
    def load_latest_state_from_blob_sync(usuario_executor: str, project_id: Optional[str] = None, nome_projeto: Optional[str] = None, report_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        import asyncio
        try:
            return asyncio.run(ProjectStateService.load_latest_state_from_blob(usuario_executor, project_id, nome_projeto, report_type))
        except RuntimeError:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
                return loop.run_until_complete(ProjectStateService.load_latest_state_from_blob(usuario_executor, project_id, nome_projeto, report_type))
            else:
                return loop.run_until_complete(ProjectStateService.load_latest_state_from_blob(usuario_executor, project_id, nome_projeto, report_type))

    @staticmethod
    async def _get_project_id_by_name(usuario_executor: str, nome_projeto: str) -> Optional[str]:
        cache_key = f"{usuario_executor}:{nome_projeto}"
        
        # 1. Tenta pegar do cache local da memória
        if cache_key in ProjectStateService._project_id_cache:
            return ProjectStateService._project_id_cache[cache_key]
        
        # 2. Se não estiver no cache, busca no Blob Storage
        state = await ProjectStateService.load_latest_state_from_blob(
            usuario_executor, 
            project_id=None, 
            nome_projeto=nome_projeto
        )
        
        # 3. Se encontrou, atualiza o cache e retorna
        if state and state.get("project_id"):
            project_id = state.get("project_id")
            ProjectStateService._project_id_cache[cache_key] = project_id
            return project_id
            
        return None

    @staticmethod
    def _invalidate_project_id_cache(nome_projeto: str):
        # Invalida entradas de cache relacionadas a este projeto
        keys_to_remove = [k for k in ProjectStateService._project_id_cache if k.endswith(f":{nome_projeto}")]
        for k in keys_to_remove:
            del ProjectStateService._project_id_cache[k]

    @staticmethod
    async def load_all_states_from_blob(usuario_executor: str, project_id: str) -> Dict[str, Any]:
        logger.info(f"Carregando todos os estados para usuario={usuario_executor}, project_id={project_id}")
        _, container_client = _get_blob_clients()
        
        # 1. Carregar o Resumo
        nome_projeto = None
        resumo_state = None
        
        # Busca blobs de resumo
        prefix_resumo = f"{usuario_executor}/"
        blobs_resumo = list(container_client.list_blobs(name_starts_with=prefix_resumo))
        
        candidatos_resumo = []
        for blob in blobs_resumo:
            # Filtra apenas arquivos json de resumo
            if blob.name.endswith('.json') and "estado_resumo_" in blob.name:
                blob_client = container_client.get_blob_client(blob.name)
                state_bytes = blob_client.download_blob().readall()
                state = json.loads(state_bytes.decode("utf-8"))
                
                # Verifica se o ID bate
                pid = state.get("project_id")
                if pid == project_id:
                    candidatos_resumo.append((blob, state))

        if candidatos_resumo:
            # Ordena para pegar o mais recente
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
            # Se não achar o resumo, não tem como buscar o resto (precisamos do nome do projeto para o path)
            return {}

        # 2. Carregar os outros relatórios
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
                # Caminho: user/projeto/estados/tipo/arquivo.json
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
                    
                    # Mapeia para o nome da chave no dicionário de resposta
                    key_map = {
                        "epicos_report": "epicos",
                        "features_report": "features",
                        "times_descricao_report": "times_descricao",
                        "alocacao_times_report": "alocacao_times",
                        "premissas_riscos_report": "premissas_riscos"
                    }
                    states_dict[key_map[report_type]] = latest_state

        return EstadoCompletoProjetoResponse(**states_dict).dict()
