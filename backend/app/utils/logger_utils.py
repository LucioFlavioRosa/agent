import logging
import json
from datetime import datetime

def _json_log(msg_dict):
    try:
        logging.info(json.dumps(msg_dict, ensure_ascii=False))
    except Exception as e:
        logging.error(f"Erro ao serializar log estruturado: {e}. Dados: {msg_dict}")

def log_request_received(endpoint: str, payload: dict):
    _json_log({
        "event": "request_received",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoint": endpoint,
        "payload": payload
    })

def log_validation_step(step_name: str, status: str, details: str = None):
    _json_log({
        "event": "validation_step",
        "timestamp": datetime.utcnow().isoformat(),
        "step_name": step_name,
        "status": status,
        "details": details
    })

def log_service_call(service_name: str, action: str, params: dict = None, extra: dict = None):
    msg = {
        "event": "service_call",
        "timestamp": datetime.utcnow().isoformat(),
        "service_name": service_name,
        "action": action,
        "params": params or {}
    }
    if extra:
        msg.update(extra)
    _json_log(msg)

def log_response_sent(endpoint: str, status_code: int, response_summary: dict):
    _json_log({
        "event": "response_sent",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoint": endpoint,
        "status_code": status_code,
        "response_summary": response_summary
    })
