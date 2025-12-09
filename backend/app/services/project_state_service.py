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
        """
        Salva o estado atual do projeto no Blob Storage.
        Identifica automaticamente se é um resumo ou um relatório específico (épicos, features, etc)
        baseado nas chaves presentes no dicionário.
        """
        logger = logging.getLogger("ProjectStateService")
        
        # 1. Converter para dicionário (suporta Pydantic v1/v2, Dict ou Objeto genérico)
        if hasattr(state_data, "dict"):
            data = state_data.dict()
        elif hasattr(state_data, "model_dump"): # Suporte a Pydantic v2
            data = state_data.model_dump()
        elif isinstance(state_data, dict):
            data = state_data
        else:
            data = state_data.__dict__

        # 2. Extrair metadados obrigatórios para montar o caminho
        usuario_executor = data.get("usuario_executor")
        nome_projeto = data.get("nome_projeto")

        if not usuario_executor or not nome_projeto:
            error_msg = f"Não é possível salvar estado: 'usuario_executor' ({usuario_executor}) ou 'nome_projeto' ({nome_projeto}) ausentes."
            logger.error(error_msg)
            raise ValueError(error_msg)

        # 3. Determinar o tipo de relatório e a subpasta correta
        subfolder_map = {
            "epicos_report": "epicos",
            "features_report": "features",
            "times_descricao_report": "times_descricao",
            "alocacao_times_report": "alocacao_times",
            "premissas_riscos_report": "premissas_riscos"
        }

        report_type = "resumo"
        subfolder = "resumo"

        # Verifica se existe alguma das chaves de relatório no dicionário
        for key, folder in subfolder_map.items():
            if key in data and data[key]: # Verifica se a chave existe e não é vazia/None
                report_type = key
                subfolder = folder
                break
        
        # 4. Gerar nome do arquivo com Timestamp UTC
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        filename = f"estado_{report_type}_{timestamp}.json"
        
        # Estrutura: usuario/projeto/estados/subpasta/arquivo
        blob_path = f"{usuario_executor}/{nome_projeto}/estados/{subfolder}/{filename}"

        # 5. Realizar o Upload
        try:
            _, container_client = _get_blob_clients()
            blob_client = container_client.get_blob_client(blob_path)
            
            # Serializa para JSON (default=str lida com objetos datetime)
            json_data = json.dumps(data, default=str, ensure_ascii=False)
            
            logger.info(f"Iniciando upload de estado para: {blob_path}")
            blob_client.upload_blob(json_data, overwrite=True)
            logger.info(f"Upload concluído com sucesso: {blob_path}")
            
            return blob_client.url
            
        except Exception as e:
            logger.error(f"Erro ao salvar estado no blob: {str(e)}")
            raise e

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
        """
        Carrega todos os estados mais recentes, ordenando explicitamente pelo timestamp extraído do nome do arquivo.
        """
        logger.info(f"Carregando todos os estados para usuario={usuario_executor}, project_id={project_id}")
        _, container_client = _get_blob_clients()
        nome_projeto = None
        resumo_state = None
        
        # --- FUNÇÃO AUXILIAR DE ORDENAÇÃO ---
        def extract_timestamp_from_filename(blob_name: str) -> datetime.datetime:
            try:
                # Esperado: .../estado_TIPO_20251209T184457Z.json
                # Pega a parte final: 20251209T184457Z
                ts_str = blob_name.split("_")[-1].replace(".json", "")
                return datetime.datetime.strptime(ts_str, "%Y%m%dT%H%M%SZ")
            except Exception:
                return datetime.datetime.min

        prefix_resumo = f"{usuario_executor}/"
        blobs_resumo = list(container_client.list_blobs(name_starts_with=prefix_resumo))
        
        # --- 1. BUSCA DO RESUMO ---
        candidatos_resumo = []
        for blob in blobs_resumo:
            if blob.name.endswith('.json') and "estado_resumo_" in blob.name:
                blob_client = container_client.get_blob_client(blob.name)
                state_bytes = blob_client.download_blob().readall()
                state = json.loads(state_bytes.decode("utf-8"))
                
                # Validação de ID
                pid = state.get("project_id")
                if not pid: 
                     # Fallback
                     pid = validate_and_fix_project_id(state, usuario_executor, state.get("nome_projeto", ""))

                if pid == project_id:
                    candidatos_resumo.append((blob, state))
        
        if candidatos_resumo:
            # Ordena usando a função auxiliar
            candidatos_resumo.sort(key=lambda item: extract_timestamp_from_filename(item[0].name), reverse=True)
            resumo_state = candidatos_resumo[0][1]
            nome_projeto = resumo_state.get("nome_projeto")
            logger.info(f"[RESUMO] Selecionado arquivo mais recente: {candidatos_resumo[0][0].name}")
        else:
            return {}

        # --- 2. BUSCA DOS RELATÓRIOS ---
        states_dict = {
            "resumo": resumo_state,
            "epicos": None,
            "features": None,
            "times_descricao": None,
            "alocacao_times": None,
            "premissas_riscos": None
        }

        if nome_projeto:
            report_types = ["epicos_report", "features_report", "times_descricao_report", "alocacao_times_report", "premissas_riscos_report"]
            subfolder_map = {
                "epicos_report": "epicos",
                "features_report": "features",
                "times_descricao_report": "times_descricao",
                "alocacao_times_report": "alocacao_times",
                "premissas_riscos_report": "premissas_riscos"
            }
            key_map = {
                "epicos_report": "epicos",
                "features_report": "features",
                "times_descricao_report": "times_descricao",
                "alocacao_times_report": "alocacao_times",
                "premissas_riscos_report": "premissas_riscos"
            }

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
                    # Ordena usando a função auxiliar
                    candidatos_report.sort(key=lambda item: extract_timestamp_from_filename(item[0].name), reverse=True)
                    
                    latest_state = candidatos_report[0][1]
                    logger.info(f"[{report_type}] Selecionado arquivo mais recente: {candidatos_report[0][0].name}")
                    
                    # Coding Defensivo (Datas)
                    agora_iso = datetime.datetime.utcnow().isoformat()
                    if "ultima_atualizacao" not in latest_state:
                        latest_state["ultima_atualizacao"] = latest_state.get("created_at") or agora_iso
                    if "created_at" not in latest_state:
                        latest_state["created_at"] = latest_state.get("ultima_atualizacao") or agora_iso
                    if "nome_projeto" not in latest_state:
                        latest_state["nome_projeto"] = nome_projeto
                    if "project_id" not in latest_state:
                        latest_state["project_id"] = project_id

                    chave_destino = key_map.get(report_type)
                    if chave_destino:
                        states_dict[chave_destino] = latest_state
        
        return EstadoCompletoProjetoResponse(**states_dict).dict()
