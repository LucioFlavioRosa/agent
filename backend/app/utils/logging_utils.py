import logging
import json
from datetime import datetime

# Utilitário para logs estruturados em JSON

def _get_timestamp():
    return datetime.utcnow().isoformat()


def _log_json(level, context, data):
    log_record = {
        "timestamp": _get_timestamp(),
        "level": level,
        "context": context,
        "data": data
    }
    logging.log(_level_to_int(level), json.dumps(log_record))


def _level_to_int(level):
    levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    return levels.get(level.upper(), logging.INFO)


def log_request_received(endpoint, payload, job_id=None, project_id=None):
    _log_json("INFO", "request_received", {
        "endpoint": endpoint,
        "payload": payload,
        "job_id": job_id,
        "project_id": project_id
    })


def log_validation_step(step, status, details=None, job_id=None, project_id=None):
    _log_json("INFO", "validation_step", {
        "step": step,
        "status": status,
        "details": details,
        "job_id": job_id,
        "project_id": project_id
    })


def log_service_call(service, action, payload=None, response=None, job_id=None, project_id=None):
    _log_json("INFO", "service_call", {
        "service": service,
        "action": action,
        "payload": payload,
        "response": response,
        "job_id": job_id,
        "project_id": project_id
    })


def log_response_sent(endpoint, response, job_id=None, project_id=None):
    _log_json("INFO", "response_sent", {
        "endpoint": endpoint,
        "response": response,
        "job_id": job_id,
        "project_id": project_id
    })


def log_error(context, error_message, exception=None, job_id=None, project_id=None):
    _log_json("ERROR", "error", {
        "context": context,
        "error_message": error_message,
        "exception": str(exception) if exception else None,
        "job_id": job_id,
        "project_id": project_id
    })
