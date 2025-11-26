import logging
from typing import Optional

def init_logger(name: Optional[str] = None):
    logger_name = name if name else "agente_revisor_board"
    logger = logging.getLogger(logger_name)
    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

def log_custom_data(job_id: str, projeto: Optional[str], data_hora: str, tokens_in: int, tokens_out: int, status: str, tipo_repositorio: str, nome_repositorio: str, tipo_analise: str, model_name: Optional[str], modo_adicao_incremental: bool, usuario_executor: Optional[str]):
    logger = logging.getLogger("agente_revisor_board")
    logger.info(f"JobID: {job_id}, Projeto: {projeto}, DataHora: {data_hora}, TokensIn: {tokens_in}, TokensOut: {tokens_out}, Status: {status}, TipoRepositorio: {tipo_repositorio}, NomeRepositorio: {nome_repositorio}, TipoAnalise: {tipo_analise}, ModelName: {model_name}, ModoAdicaoIncremental: {modo_adicao_incremental}, UsuarioExecutor: {usuario_executor}")
