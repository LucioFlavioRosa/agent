import logging
import json
from typing import Optional

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        # Evita duplicar os logs se o logger já tiver sido instanciado
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            # Formato limpo, o corpo do JSON vai dentro da mensagem
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _build_msg(self, event: str, message: str, **kwargs) -> str:
        """Monta o log em um dicionário limpo e converte para string JSON."""
        log_data = {"event": event, "msg": message}
        # Adiciona apenas as chaves que não são nulas
        for key, value in kwargs.items():
            if value is not None:
                log_data[key] = value
                
        return json.dumps(log_data, ensure_ascii=False)

    def log_info_negocio(self, event: str, message: str, job_id: Optional[str] = None, company_id: Optional[str] = None, extra: dict = None):
        extra = extra or {}
        msg = self._build_msg(event, message, job_id=job_id, company_id=company_id, **extra)
        self.logger.info(msg)

    def log_erro(self, event: str, message: str, job_id: Optional[str] = None, company_id: Optional[str] = None, extra: dict = None):
        extra = extra or {}
        msg = self._build_msg(event, message, job_id=job_id, company_id=company_id, **extra)
        self.logger.error(msg)

    def log_evento(self, level: str, event: str, mensagem: str, extra: dict = None):
        extra = extra or {}
        msg = self._build_msg(event, mensagem, **extra)
        if level.upper() == "ERROR":
            self.logger.error(msg)
        elif level.upper() == "WARNING":
            self.logger.warning(msg)
        else:
            self.logger.info(msg)
