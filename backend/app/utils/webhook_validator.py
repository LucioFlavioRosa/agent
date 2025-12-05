import logging
from backend.app.core.config import settings

def validate_report_data_structure(report_type: str, report_data: dict, analysis_type: str) -> bool:
    logger = logging.getLogger("webhook_validator")
    if not isinstance(report_data, dict):
        logger.error(f"report_data não é um dicionário: {type(report_data)}")
        return False
    mcp_config_registry = getattr(settings, "mcp_config_registry", None)
    if not mcp_config_registry or not hasattr(mcp_config_registry, "agents"):
        logger.warning("mcp_config_registry não está configurado corretamente. Validação ignorada.")
        return True
    agents = mcp_config_registry.agents
    if analysis_type not in agents:
        logger.warning(f"analysis_type '{analysis_type}' não encontrado em mcp_config_registry. Validação ignorada.")
        return True
    agent_cfg = agents[analysis_type]
    if not hasattr(agent_cfg, "report_mapping"):
        logger.warning(f"Agent config para '{analysis_type}' não possui report_mapping. Validação ignorada.")
        return True
    expected_field = agent_cfg.report_mapping.get(report_type)
    if not expected_field:
        logger.warning(f"report_type '{report_type}' não mapeado para analysis_type '{analysis_type}'. Validação ignorada.")
        return True
    if expected_field not in report_data:
        logger.error(f"Campo '{expected_field}' ausente em report_data para report_type '{report_type}' e analysis_type '{analysis_type}'.")
        return False
    return True
