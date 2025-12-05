import logging
from backend.app.core.config import settings

def validate_report_data_structure(report_type: str, report_data: dict, analysis_type: str) -> bool:
    logger = logging.getLogger("webhook_validator")
    if not isinstance(report_data, dict):
        logger.error(f"report_data não é um dicionário: {type(report_data)}")
        return False
    if report_type == "epicos":
        if "epicos" not in report_data:
            logger.error(f"Campo 'epicos' ausente em report_data para report_type 'epicos'.")
            return False
    elif report_type == "features":
        if "features" not in report_data:
            logger.error(f"Campo 'features' ausente em report_data para report_type 'features'.")
            return False
    elif report_type == "times_descricao":
        if "times_descricao" not in report_data:
            logger.error(f"Campo 'times_descricao' ausente em report_data para report_type 'times_descricao'.")
            return False
    elif report_type == "alocacao_times":
        if "alocacao_times" not in report_data:
            logger.error(f"Campo 'alocacao_times' ausente em report_data para report_type 'alocacao_times'.")
            return False
    elif report_type == "premissas_riscos":
        if "premissas_riscos" not in report_data:
            logger.error(f"Campo 'premissas_riscos' ausente em report_data para report_type 'premissas_riscos'.")
            return False
    else:
        logger.error(f"report_type '{report_type}' não reconhecido.")
        return False
    return True
