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
        session_id = state.get("session_id")
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        blob_folder = f"{usuario_executor}/{projeto}/estados"
        blob_filename = f"estado_{session_id}_{timestamp}.json"
        blob_path = f"{blob_folder}/{blob_filename}"
        _, container_client = _get_blob_clients()
        blob_client = container_client.get_blob_client(blob_path)
        logger = logging.getLogger("ProjectStateService")
        logger.info(f"[save_state_to_blob] Iniciando persistência no Blob Storage: {blob_path}")
        logger.info(f"[save_state_to_blob] epicos_report: {json.dumps(state.get('epicos_report', {}), ensure_ascii=False)}")
        logger.info(f"[save_state_to_blob] features_report: {json.dumps(state.get('features_report', {}), ensure_ascii=False)}")
        logger.info(f"[save_state_to_blob] times_descricao_report: {json.dumps(state.get('times_descricao_report', {}), ensure_ascii=False)}")
        logger.info(f"[save_state_to_blob] alocacao_times_report: {json.dumps(state.get('alocacao_times_report', {}), ensure_ascii=False)}")
        logger.info(f"[save_state_to_blob] premissas_riscos_report: {json.dumps(state.get('premissas_riscos_report', {}), ensure_ascii=False)}")
        blob_client.upload_blob(json.dumps(state, ensure_ascii=False, separators=(',', ':')).encode("utf-8"), overwrite=True, content_settings=None)
        logger.info(f"[save_state_to_blob] Persistência concluída no Blob Storage: {blob_path}")
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
        # Retrocompatibilidade: se o estado antigo tiver apenas 'reports', migrar para os campos individuais
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
        # Garante que todos os campos existem, mesmo que None
        for k in ['epicos_report', 'features_report', 'times_descricao_report', 'alocacao_times_report', 'premissas_riscos_report']:
            if k not in state:
                state[k] = None
        return state
