import logging
import json
from typing import Optional

logger = logging.getLogger("agente_logger")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)

def init_logger():
    pass

def log_custom_data(
    job_id: Optional[str] = None,
    project_id: Optional[str] = None,
    data_hora: Optional[str] = None,
    tipo_analise: Optional[str] = None,
    model_name: Optional[str] = None,
    tokens_in: Optional[int] = None,
    tokens_out: Optional[int] = None
):
    log_entry = {
        "job_id": job_id,
        "project_id": project_id,
        "data_hora": data_hora,
        "tipo_analise": tipo_analise,
        "model_name": model_name,
        "tokens_entrada": tokens_in,
        "tokens_saida": tokens_out
    }
    logger.info(json.dumps(log_entry))
