import logging
import sys
import threading
from typing import Optional

_logger = None
_logger_lock = threading.Lock()
def init_logger():
    global _logger
    with _logger_lock:
        if _logger is None:
            _logger = logging.getLogger("agente_revisor_board")
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(message)s')
            handler.setFormatter(formatter)
            _logger.addHandler(handler)
            _logger.setLevel(logging.INFO)

def log_custom_data(**kwargs):
    global _logger
    if _logger is None:
        init_logger()
    _logger.info(f"DADOS CUSTOM: {kwargs}")
