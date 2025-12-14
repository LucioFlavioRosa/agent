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
                if not project_id:
                     project_id = validate_and_fix_project_id(state, usuario_executor, state.get("nome_projeto", ""))
                
                if nome_blob == nome_projeto_normalizado and project_id:
                    ProjectStateService._project_id_cache[cache_key] = project_id
                    return project_id
        return None

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
            blob_client.upload_blob(json_data, overwrite=True)
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
                # Download e parse
                try:
                    state_bytes = blob_client.download_blob().readall()
                    state = json.loads(state_bytes.decode("utf-8"))
                except Exception as e:
                    logger.warning(f"Erro ao ler JSON do blob {blob.name}: {e}")
                    continue

                pid = state.get("project_id")
                # Validação de Project ID (se necessário corrigir)
                if not pid or not isinstance(pid, str) or not pid.strip():
                    pid = validate_and_fix_project_id(state, usuario_executor, state.get("nome_projeto", ""))

                # 1. Lógica de FILTRO (Quem entra na lista de candidatos?)
                match = False
                if project_id:
                    if pid == project_id:
                        match = True
                elif nome_projeto:
                    # Se não tem ID, tenta pelo nome
                    nome_blob = ProjectStateService._normalize_nome_projeto(state.get("nome_projeto", ""))
                    nome_target = ProjectStateService._normalize_nome_projeto(nome_projeto)
                    if nome_blob == nome_target:
                        match = True
                
                if match:
                    states.append((blob, state))

        # 2. Lógica de ORDENAÇÃO (Quem é o mais recente?)
        if states:
            def get_sort_key(item):
                blob_obj, state_dict = item
                
                # PRIORIDADE 1: Timestamp no NOME DO ARQUIVO (A fonte mais confiável de "criação")
                # Ex esperado: estado_epicos_20251213T231912Z.json
                try:
                    # Pega a última parte depois do "_" e remove a extensão
                    ts_str = blob_obj.name.split("_")[-1].replace(".json", "")
                    # Tenta converter o formato ISO compactado
                    return datetime.datetime.strptime(ts_str, "%Y%m%dT%H%M%SZ")
                except Exception:
                    # Se o nome não seguir o padrão, passamos para a próxima tentativa
                    pass

                # PRIORIDADE 2: Campo 'created_at' dentro do JSON
                if state_dict.get("created_at"):
                    try:
                        return datetime.datetime.fromisoformat(state_dict.get("created_at"))
                    except:
                        pass
                
                # PRIORIDADE 3: Campo 'ultima_atualizacao' dentro do JSON
                if state_dict.get("ultima_atualizacao"):
                    try:
                        return datetime.datetime.fromisoformat(state_dict.get("ultima_atualizacao"))
                    except:
                        pass

                # Se tudo falhar, retorna data mínima para ir para o fim da fila
                return datetime.datetime.min
            
            # Ordena do MAIOR (mais novo) para o MENOR (mais antigo)
            states_sorted = sorted(states, key=get_sort_key, reverse=True)
            
            melhor_arquivo = states_sorted[0][0].name
            logger.info(f"[DEBUG] Estado mais recente selecionado: {melhor_arquivo} (Baseado na data de criação)")
            return states_sorted[0][1]

        logger.info(f"Nenhum estado válido encontrado para usuario_executor={usuario_executor}...")
        return None

    @staticmethod
    async def load_all_states_from_blob(usuario_executor: str, project_id: str) -> Dict[str, Any]:
        logger.info(f"Carregando todos os estados para usuario={usuario_executor}, project_id={project_id}")
        _, container_client = _get_blob_clients()
        
        def extract_timestamp_from_filename(blob_name: str) -> datetime.datetime:
            try:
                ts_str = blob_name.split("_")[-1].replace(".json", "")
                return datetime.datetime.strptime(ts_str, "%Y%m%dT%H%M%SZ")
            except Exception:
                return datetime.datetime.min

        # Variável auxiliar para capturar o ID de onde quer que ele venha
        captured_last_job_id = None

        # 1. Carregar Resumo
        prefix_resumo = f"{usuario_executor}/"
        blobs_resumo = list(container_client.list_blobs(name_starts_with=prefix_resumo))
        candidatos_resumo = []
        
        for blob in blobs_resumo:
            if blob.name.endswith('.json') and "estado_resumo_" in blob.name:
                blob_client = container_client.get_blob_client(blob.name)
                try:
                    state_bytes = blob_client.download_blob().readall()
                    state = json.loads(state_bytes.decode("utf-8"))
                    pid = state.get("project_id")
                    if not pid: pid = validate_and_fix_project_id(state, usuario_executor, state.get("nome_projeto", ""))
                    
                    if pid == project_id:
                        candidatos_resumo.append((blob, state))
                except:
                    continue

        resumo_state = None
        nome_projeto = None
        
        if candidatos_resumo:
            candidatos_resumo.sort(key=lambda item: extract_timestamp_from_filename(item[0].name), reverse=True)
            resumo_state = candidatos_resumo[0][1]
            nome_projeto = resumo_state.get("nome_projeto")
            
            # Tenta capturar do resumo
            if resumo_state.get("last_job_id"):
                captured_last_job_id = resumo_state.get("last_job_id")
                
            logger.info(f"[RESUMO] Selecionado arquivo mais recente: {candidatos_resumo[0][0].name}")
        else:
            return {}

        states_dict = {
            "resumo": resumo_state,
            "epicos": None,
            "features": None,
            "times_descricao": None,
            "alocacao_times": None,
            "premissas_riscos": None
        }

        # 2. Carregar outros relatórios
        if nome_projeto:
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

            for report_type, subfolder in subfolder_map.items():
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
                    candidatos_report.sort(key=lambda item: extract_timestamp_from_filename(item[0].name), reverse=True)
                    latest_state = candidatos_report[0][1]
                    
                    # Tenta capturar do relatório específico (O mais provável!)
                    if latest_state.get("last_job_id"):
                        captured_last_job_id = latest_state.get("last_job_id")

                    agora_iso = datetime.datetime.utcnow().isoformat()
                    if "ultima_atualizacao" not in latest_state: latest_state["ultima_atualizacao"] = agora_iso
                    if "created_at" not in latest_state: latest_state["created_at"] = agora_iso
                    if "nome_projeto" not in latest_state: latest_state["nome_projeto"] = nome_projeto
                    
                    chave_destino = key_map.get(report_type)
                    if chave_destino:
                        states_dict[chave_destino] = latest_state

        # 3. CONSTRUÇÃO FINAL DA RESPOSTA
        try:
            response_obj = EstadoCompletoProjetoResponse(**states_dict)
            final_dict = response_obj.dict()
        except Exception as e:
            logger.error(f"Erro na validação Pydantic em load_all_states: {e}. Retornando dict bruto.")
            final_dict = states_dict

        # 4. INJEÇÃO CRÍTICA DO LAST_JOB_ID (Usando a variável capturada)
        if captured_last_job_id:
            final_dict["last_job_id"] = captured_last_job_id
            logger.info(f"✅ last_job_id ({captured_last_job_id}) preservado e injetado na resposta.")
        
        return final_dict
