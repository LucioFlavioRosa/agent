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
        project_id = state.get("project_id")
        nome_projeto = state.get("nome_projeto") or projeto
        state["project_id"] = project_id
        state["nome_projeto"] = nome_projeto
        state["docx_blob_url"] = state.get("docx_blob_url")
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        blob_folder = f"{usuario_executor}/{projeto}/estados"
        blob_filename = f"estado_{timestamp}.json"
        blob_path = f"{blob_folder}/{blob_filename}"
        _, container_client = _get_blob_clients()
        blob_client = container_client.get_blob_client(blob_path)
        blob_client.upload_blob(json.dumps(state, ensure_ascii=False, separators=(',', ':')).encode("utf-8"), overwrite=True, content_settings=None)
        return blob_client.url

    @staticmethod
    async def load_latest_state_from_blob(usuario_executor: str, project_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        logger = logging.getLogger("ProjectStateService")
        if project_id:
            _, container_client = _get_blob_clients()
            prefix = f"{usuario_executor}/"
            blobs = list(container_client.list_blobs(name_starts_with=prefix))
            for blob in blobs:
                if blob.name.endswith('.json'):
                    blob_client = container_client.get_blob_client(blob.name)
                    state_bytes = blob_client.download_blob().readall()
                    state = json.loads(state_bytes.decode("utf-8"))
                    if state.get("project_id") == project_id:
                        logger.info(f"Estado carregado com sucesso para usuario_executor={usuario_executor}, project_id={project_id}")
                        return state
            logger.info(f"Nenhum estado encontrado para usuario_executor={usuario_executor}, project_id={project_id}")
            return None
        else:
            logger.info(f"Nenhum parâmetro fornecido para buscar estado.")
            return None

    @staticmethod
    async def _get_project_id_by_name(usuario_executor: str, nome_projeto: str) -> Optional[str]:
        _, container_client = _get_blob_clients()
        prefix = f"{usuario_executor}/"
        blobs = list(container_client.list_blobs(name_starts_with=prefix))
        for blob in blobs:
            if blob.name.endswith('.json'):
                blob_client = container_client.get_blob_client(blob.name)
                state_bytes = blob_client.download_blob().readall()
                state = json.loads(state_bytes.decode("utf-8"))
                if state.get("projeto") == nome_projeto:
                    return state.get("project_id")
        return None

    @staticmethod
    async def get_latest_analysis_metadata(usuario_executor: str, project_id: Optional[str] = None) -> Dict[str, str]:
        state = await ProjectStateService.load_latest_state_from_blob(usuario_executor, project_id=project_id)
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
                    "nome_projeto": state.get("nome_projeto", projeto),
                    "analysis_type": state.get("analysis_type"),
                    "created_at": state.get("created_at"),
                    "last_saved_to_blob": state.get("last_saved_to_blob"),
                    "project_id": state.get("project_id"),
                    "docx_blob_url": state.get("docx_blob_url"),
                    "docx_files": state.get("docx_files", []),
                    "comentario_usuario": state.get("comentario_usuario"),
                    "extracted_text": state.get("extracted_text"),
                    "epicos_report": state.get("epicos_report"),
                    "features_report": state.get("features_report"),
                    "times_descricao_report": state.get("times_descricao_report"),
                    "alocacao_times_report": state.get("alocacao_times_report"),
                    "premissas_riscos_report": state.get("premissas_riscos_report")
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
