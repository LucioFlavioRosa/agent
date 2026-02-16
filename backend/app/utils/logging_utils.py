import logging

logger = logging.getLogger()

def _get_timestamp():
    from datetime import datetime
    return datetime.utcnow().isoformat()

def _log_structured(level, context, data, job_id=None, project_id=None):
    """
    Função interna que envia o dicionário puro para o logger via 'extra'.
    O Formatter no main.py será responsável por transformar isso em JSON.
    """
    # Monta os dados estruturados
    extra_fields = {
        "context": context,
        "data": data,
        "job_id": job_id,
        "project_id": project_id
    }
    
    # Remove campos nulos para limpar o log
    extra_fields = {k: v for k, v in extra_fields.items() if v is not None}

    # Mapeamento de níveis de string para inteiros do logging
    levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    level_int = levels.get(level.upper(), logging.INFO)

    # A mensagem principal será simples, pois os detalhes estarão no JSON raiz
    msg = f"[{context}] Log estruturado"

    # O PULO DO GATO: Passamos o dict no parâmetro 'extra'
    logger.log(level_int, msg, extra=extra_fields)

# --- Funções Públicas (Assinaturas mantidas) ---

def log_request_received(endpoint, payload, job_id=None, project_id=None):
    _log_structured("INFO", "request_received", {
        "endpoint": endpoint,
        "payload": payload
    }, job_id, project_id)

def log_validation_step(step, status, details=None, job_id=None, project_id=None):
    _log_structured("INFO", "validation_step", {
        "step": step,
        "status": status,
        "details": details
    }, job_id, project_id)

def log_service_call(service, action, payload=None, response=None, job_id=None, project_id=None):
    _log_structured("INFO", "service_call", {
        "service": service,
        "action": action,
        "payload": payload,
        "response": response
    }, job_id, project_id)

def log_response_sent(endpoint, response, job_id=None, project_id=None):
    _log_structured("INFO", "response_sent", {
        "endpoint": endpoint,
        "response": response
    }, job_id, project_id)

def log_error(context, error_message, exception=None, job_id=None, project_id=None):
    _log_structured("ERROR", "error", {
        "sub_context": context,
        "error_message": error_message,
        "exception": str(exception) if exception else None
    }, job_id, project_id)
