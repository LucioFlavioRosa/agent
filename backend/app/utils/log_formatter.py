import logging
import json
from datetime import datetime

class StructuredLogger:
    def __init__(self, module_name):
        self.module_name = module_name
        self.logger = logging.getLogger(module_name)

    def _build_log(self, level, event, mensagem, job_id=None, company_id=None, project_id=None, extra=None):
        log_dict = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "module": self.module_name,
            "event": event,
            "job_id": job_id,
            "company_id": company_id,
            "project_id": project_id,
            "mensagem": mensagem
        }
        if extra:
            log_dict.update(extra)
        return json.dumps({k: v for k, v in log_dict.items() if v is not None})

    def log_entrada_funcao(self, func_name, job_id=None, company_id=None, project_id=None, mensagem=None, extra=None):
        msg = mensagem or f"Entrada na função {func_name}"
        self.logger.info(self._build_log("INFO", f"entrada_{func_name}", msg, job_id, company_id, project_id, extra))

    def log_saida_funcao(self, func_name, job_id=None, company_id=None, project_id=None, mensagem=None, extra=None):
        msg = mensagem or f"Saída da função {func_name}"
        self.logger.info(self._build_log("INFO", f"saida_{func_name}", msg, job_id, company_id, project_id, extra))

    def log_erro(self, event, mensagem, job_id=None, company_id=None, project_id=None, extra=None):
        self.logger.error(self._build_log("ERROR", event, mensagem, job_id, company_id, project_id, extra))

    def log_info_negocio(self, event, mensagem, job_id=None, company_id=None, project_id=None, extra=None):
        self.logger.info(self._build_log("INFO", event, mensagem, job_id, company_id, project_id, extra))

    def log_evento(self, level, event, mensagem, job_id=None, company_id=None, project_id=None, extra=None):
        if level == "ERROR":
            self.logger.error(self._build_log(level, event, mensagem, job_id, company_id, project_id, extra))
        else:
            self.logger.info(self._build_log(level, event, mensagem, job_id, company_id, project_id, extra))
