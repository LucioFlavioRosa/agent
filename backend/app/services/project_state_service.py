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

    # ... (restante do arquivo permanece igual)
