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
    projeto: Optional[str] = None,
    data_hora: Optional[str] = None,
    status: Optional[str] = None,
    tipo_repositorio: Optional[str] = None,
    nome_repositorio: Optional[str] = None,
    tipo_analise: Optional[str] = None,
    model_name: Optional[str] = None,
    tokens_in: Optional[int] = None,
    tokens_out: Optional[int] = None,
    modo_adicao_incremental: Optional[bool] = None,
    usuario_executor: Optional[str] = None
):
    log_entry = {
        "job_id": job_id,
        "projeto": projeto,
        "data_hora": data_hora,
        "status": status,
        "tipo_repositorio": tipo_repositorio,
        "nome_repositorio": nome_repositorio,
        "tipo_analise": tipo_analise,
        "model_name": model_name,
        "tokens_entrada": tokens_in,
        "tokens_saida": tokens_out,
        "modo_adicao_incremental": modo_adicao_incremental,
        "usuario_executor": usuario_executor
    }
    logger.info(json.dumps(log_entry))