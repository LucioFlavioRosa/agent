import logging
import json
from typing import Optional
from backend.app.config.analysis_context_enrichment import ANALYSIS_CONTEXT_CONFIG
from backend.app.services.project_state_service import ProjectStateService

class ContextEnrichmentService:
    @staticmethod
    async def enrich_instructions(project_id: str, analysis_type: str, instrucoes_extras: Optional[str]) -> str:
        logger = logging.getLogger("ContextEnrichmentService")
        logger.debug(f"[ENRICH] analysis_type={analysis_type}, project_id={project_id}, instrucoes_extras (orig): '{instrucoes_extras}'")
        config_entries = ANALYSIS_CONTEXT_CONFIG.get(analysis_type)
        logger.debug(f"[ENRICH] config_entries: {config_entries}")
        if not config_entries:
            logger.debug("[ENRICH] Nenhuma configuração encontrada para analysis_type. Retornando instrucoes_extras original.")
            return instrucoes_extras or ""
        enriched_parts = []
        estados_lidos = 0
        for entry in config_entries:
            estado_para_ler = entry.get("estado_para_ler")
            report_para_ler = entry.get("report_para_ler")
            logger.debug(f"[ENRICH] Loop: estado_para_ler={estado_para_ler}, report_para_ler={report_para_ler}")
            if not estado_para_ler or not report_para_ler:
                logger.warning(f"Configuração inválida para analysis_type={analysis_type}: {entry}")
                continue
            try:
                logger.debug(f"[ENRICH] Chamando ProjectStateService.load_latest_state_from_blob(project_id={project_id}, report_type={report_para_ler})")
                state = await ProjectStateService.load_latest_state_from_blob(
                    usuario_executor=None,
                    project_id=project_id,
                    nome_projeto=None,
                    report_type=report_para_ler
                )
                logger.debug(f"[ENRICH] Estado retornado: tipo={type(state)}, chaves={list(state.keys()) if isinstance(state, dict) else 'N/A'}")
                if not state:
                    logger.warning(f"Estado '{estado_para_ler}' não encontrado para project_id={project_id}")
                    continue
                report_content = state.get(report_para_ler)
                if report_content is None or (isinstance(report_content, str) and not report_content.strip()) or (isinstance(report_content, dict) and not report_content):
                    logger.warning(f"Campo '{report_para_ler}' ausente ou vazio no estado '{estado_para_ler}' para project_id={project_id}")
                    continue
                try:
                    report_str = json.dumps(report_content, ensure_ascii=False, indent=2)
                except Exception:
                    report_str = str(report_content)
                logger.debug(f"[ENRICH] report_str tamanho={len(report_str)}, preview={report_str[:200]}")
                enriched_parts.append(f"[{report_para_ler}]:\n{report_str}")
                estados_lidos += 1
            except Exception as e:
                logger.warning(f"Erro ao buscar/serializar estado '{estado_para_ler}' para project_id={project_id}: {e}")
                continue
        if instrucoes_extras:
            enriched_parts.append(instrucoes_extras)
        enriched_text = "\n\n".join(enriched_parts)
        logger.debug(f"[ENRICH] instrucoes_extras ENRIQUECIDO: '{enriched_text}'")
        if config_entries and estados_lidos > 0:
            algum_report = False
            for entry in config_entries:
                report_para_ler = entry.get("report_para_ler")
                if report_para_ler and f"[{report_para_ler}]" in enriched_text:
                    algum_report = True
                    break
            if not algum_report:
                logger.error(f"[ENRICH] ERRO: Texto enriquecido não contém conteúdo do report para analysis_type={analysis_type}, project_id={project_id}")
        return enriched_text
