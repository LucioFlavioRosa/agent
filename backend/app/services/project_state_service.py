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
        missing_fields = []
        # Garante que todos os campos de relatório estejam presentes
        for k in REPORT_FIELDS:
            if k not in state:
                logger.critical(f"[save_state_to_blob] Campo de relatório '{k}' ausente, preenchendo com None.")
                state[k] = None
                missing_fields.append(k)
        logger.info(f"[save_state_to_blob] Conteúdo dos campos de relatório antes de salvar:")
        for k in REPORT_FIELDS:
            logger.info(f"[save_state_to_blob] {k}: {json.dumps(state.get(k, None), ensure_ascii=False)}")
        blob_client.upload_blob(json.dumps(state, ensure_ascii=False, separators=(',', ':')).encode("utf-8"), overwrite=True, content_settings=None)
        logger.info(f"[save_state_to_blob] Persistência concluída no Blob Storage: {blob_path}")
        if missing_fields:
            logger.critical(f"[save_state_to_blob] Os seguintes campos de relatório estavam ausentes e foram preenchidos com None: {missing_fields}")
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
        missing_fields = []
        for k in REPORT_FIELDS:
            if k not in state:
                logger.warning(f"[load_latest_state_from_blob] Campo de relatório '{k}' ausente, preenchendo com None.")
                state[k] = None
                missing_fields.append(k)
        logger.info(f"[load_latest_state_from_blob] Conteúdo dos campos de relatório após carregar do Blob:")
        for k in REPORT_FIELDS:
            logger.info(f"[load_latest_state_from_blob] {k}: {json.dumps(state.get(k, None), ensure_ascii=False)}")
        if missing_fields:
            logger.warning(f"[load_latest_state_from_blob] Os seguintes campos de relatório estavam ausentes e foram preenchidos com None: {missing_fields}")
        return state

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
        missing_fields = []
        for k in REPORT_FIELDS:
            if k not in state:
                logger.warning(f"[load_latest_state_by_session_id] Campo de relatório '{k}' ausente, preenchendo com None.")
                state[k] = None
                missing_fields.append(k)
        for k in REPORT_FIELDS:
            logger.info(f"[load_latest_state_by_session_id] {k}: {json.dumps(state.get(k, None), ensure_ascii=False)}")
        if missing_fields:
            logger.warning(f"[load_latest_state_by_session_id] Os seguintes campos de relatório estavam ausentes e foram preenchidos com None: {missing_fields}")
        return state
