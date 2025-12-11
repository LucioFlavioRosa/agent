import logging
import json
from typing import Optional
from backend.app.config.analysis_context_enrichment import ANALYSIS_CONTEXT_CONFIG
from backend.app.services.project_state_service import ProjectStateService

class ContextEnrichmentService:
    @staticmethod
    async def enrich_instructions(project_id: str, analysis_type: str, instrucoes_extras: Optional[str]) -> str:
        logger = logging.getLogger("ContextEnrichmentService")
        config_entries = ANALYSIS_CONTEXT_CONFIG.get(analysis_type)
        if not config_entries:
            return instrucoes_extras or ""
        enriched_parts = []
        estados_lidos = 0
        for entry in config_entries:
            estado_para_ler = entry.get("estado_para_ler")
            report_para_ler = entry.get("report_para_ler")
            if not estado_para_ler or not report_para_ler:
                logger.warning(f"Configuração inválida para analysis_type={analysis_type}: {entry}")
                continue
            try:
                state = await ProjectStateService.load_latest_state_from_blob(
                    usuario_executor=None,  # ProjectStateService aceita project_id
                    project_id=project_id,
                    nome_projeto=None,
                    report_type=report_para_ler
                )
                if not state:
                    logger.warning(f"Estado '{estado_para_ler}' não encontrado para project_id={project_id}")
                    continue
                report_content = state.get(report_para_ler)
                if report_content is None:
                    logger.warning(f"Campo '{report_para_ler}' ausente no estado '{estado_para_ler}' para project_id={project_id}")
                    continue
                try:
                    report_str = json.dumps(report_content, ensure_ascii=False, indent=2)
                except Exception:
                    report_str = str(report_content)
                enriched_parts.append(f"[{report_para_ler}]:\n{report_str}")
                estados_lidos += 1
            except Exception as e:
                logger.warning(f"Erro ao buscar/serializar estado '{estado_para_ler}' para project_id={project_id}: {e}")
                continue
        if instrucoes_extras:
            enriched_parts.append(instrucoes_extras)
        enriched_text = "\n\n".join(enriched_parts)
        logger.info(f"Contexto enriquecido para analysis_type={analysis_type}: {estados_lidos} estados lidos.")
        return enriched_text
