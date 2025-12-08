import logging
from backend.app.core.config import settings

def validate_report_data_structure(report_data: dict, analysis_type: str) -> bool:
    logger = logging.getLogger("webhook_validator")
    valid_report_fields = [
        "epicos_report",
        "features_report",
        "times_descricao_report",
        "alocacao_times_report",
        "premissas_riscos_report"
    ]
    if not isinstance(report_data, dict):
        logger.error(f"report_data não é um dicionário: {type(report_data)}")
        return False
    if len(report_data) != 1:
        logger.error(f"report_data deve conter exatamente uma chave, recebido: {list(report_data.keys())}")
        return False
    report_field = list(report_data.keys())[0]
    if report_field not in valid_report_fields:
        logger.error(f"Chave de relatório '{report_field}' não é válida. Esperado uma das: {valid_report_fields}")
        return False
    value = report_data[report_field]
    if not isinstance(value, list):
        logger.error(f"O valor da chave '{report_field}' deve ser uma lista.")
        return False
    unexpected_keys = set(report_data.keys()) - set(valid_report_fields)
    if unexpected_keys:
        logger.warning(f"report_data contém chaves inesperadas: {unexpected_keys}")
    return True
