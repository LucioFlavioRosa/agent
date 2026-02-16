# backend/app/utils/logging_utils.py
import logging

# Pegamos o logger raiz ou podemos aceitar um logger como argumento
logger = logging.getLogger() 

def _log_structured(level, context, data, job_id=None, project_id=None):
    # Montamos o dicionário com os campos extras
    extra_fields = {
        "context": context,
        "data": data,
        "job_id": job_id,
        "project_id": project_id
    }
    
    # Removemos chaves com valor None para limpar o log
    extra_fields = {k: v for k, v in extra_fields.items() if v is not None}

    # Enviamos como 'extra'. O Formatter do main.py vai pegar isso.
    message = f"[{context}] Action detected"
    
    # Mapeamento de níveis
    lvl_map = {
        "DEBUG": logging.DEBUG, "INFO": logging.INFO,
        "WARNING": logging.WARNING, "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    level_int = lvl_map.get(level.upper(), logging.INFO)

    logger.log(level_int, message, extra=extra_fields)

# As funções públicas continuam iguais na assinatura, só mudam a chamada interna
def log_request_received(endpoint, payload, job_id=None, project_id=None):
    _log_structured("INFO", "request_received", {"endpoint": endpoint, "payload": payload}, job_id, project_id)

def log_validation_step(step, status, details=None, job_id=None, project_id=None):
    _log_structured("INFO", "validation_step", {"step": step, "status": status, "details": details}, job_id, project_id)

def log_service_call(service, action, payload=None, response=None, job_id=None, project_id=None):
    data = {"service": service, "action": action, "payload": payload, "response": response}
    _log_structured("INFO", "service_call", data, job_id, project_id)

def log_response_sent(endpoint, response, job_id=None, project_id=None):
    _log_structured("INFO", "response_sent", {"endpoint": endpoint, "response": response}, job_id, project_id)

def log_error(context, error_message, exception=None, job_id=None, project_id=None):
    data = {"error_message": error_message, "exception": str(exception) if exception else None}
    _log_structured("ERROR", context, data, job_id, project_id)
