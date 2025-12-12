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
        # ... (Mantido igual ao seu original) ...
        # Para economizar espaço aqui, assuma que este método não mudou
        # Se precisar dele completo, avise.
        pass 

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
    async def load_latest_state_from_blob(usuario_executor: str, project_id: Optional[str] = None, nome_projeto: Optional[str] = None) -> Optional[Dict[str, Any]]:
        # ... (Mantido igual ao seu original) ...
        # Retorna o estado bruto, então aqui geralmente funciona bem.
        # Vou pular a repetição para focar no método problemático abaixo.
        pass

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

        # 1. Carregar Resumo (Onde está o last_job_id)
        prefix_resumo = f"{usuario_executor}/"
        blobs_resumo = list(container_client.list_blobs(name_starts_with=prefix_resumo))
        candidatos_resumo = []
        
        for blob in blobs_resumo:
            if blob.name.endswith('.json') and "estado_resumo_" in blob.name:
                # Otimização: ler project_id sem baixar tudo seria ideal, mas baixamos por segurança
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
            # Mapeia nome do report para chave no EstadoCompleto
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
                    
                    # Preenche campos faltantes para validação Pydantic
                    agora_iso = datetime.datetime.utcnow().isoformat()
                    if "ultima_atualizacao" not in latest_state: latest_state["ultima_atualizacao"] = agora_iso
                    if "created_at" not in latest_state: latest_state["created_at"] = agora_iso
                    if "nome_projeto" not in latest_state: latest_state["nome_projeto"] = nome_projeto
                    
                    chave_destino = key_map.get(report_type)
                    if chave_destino:
                        states_dict[chave_destino] = latest_state

        # 3. CONSTRUÇÃO FINAL DA RESPOSTA (CORRIGIDA)
        try:
            # Tenta usar o Pydantic para validar a estrutura
            response_obj = EstadoCompletoProjetoResponse(**states_dict)
            final_dict = response_obj.dict()
        except Exception as e:
            logger.error(f"Erro na validação Pydantic em load_all_states: {e}. Retornando dict bruto.")
            final_dict = states_dict

        # 4. INJEÇÃO CRÍTICA DO LAST_JOB_ID
        # Se o Pydantic removeu (porque o modelo não tem o campo), nós colocamos de volta.
        if resumo_state and "last_job_id" in resumo_state:
            final_dict["last_job_id"] = resumo_state["last_job_id"]
            logger.info(f"✅ last_job_id preservado na resposta: {final_dict['last_job_id']}")
        
        return final_dict
