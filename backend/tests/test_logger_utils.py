import logging
import json
import pytest

# Supondo que logger_utils.py existe e define uma função para logar mensagens estruturadas
from backend.app.utils.json_encoder import safe_json_dumps

class DummyRecord:
    def __init__(self, levelname, msg, funcName, timestamp=None):
        self.levelname = levelname
        self.msg = msg
        self.funcName = funcName
        self.created = timestamp or 1234567890.0

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "msg": record.getMessage(),
            "func": record.funcName
        }
        return json.dumps(log_record)

@pytest.fixture
def logger():
    logger = logging.getLogger("test_logger_utils")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.handlers.clear()
    logger.addHandler(handler)
    return logger

def test_info_log_is_structured(logger, capsys):
    logger.info("Mensagem de teste INFO")
    captured = capsys.readouterr().out
    log_json = json.loads(captured.strip())
    assert log_json["level"] == "INFO"
    assert log_json["msg"] == "Mensagem de teste INFO"
    assert "timestamp" in log_json
    assert "func" in log_json

def test_warning_log_is_structured(logger, capsys):
    logger.warning("Mensagem de teste WARNING")
    captured = capsys.readouterr().out
    log_json = json.loads(captured.strip())
    assert log_json["level"] == "WARNING"
    assert log_json["msg"] == "Mensagem de teste WARNING"


def test_error_log_is_structured(logger, capsys):
    logger.error("Mensagem de teste ERROR")
    captured = capsys.readouterr().out
    log_json = json.loads(captured.strip())
    assert log_json["level"] == "ERROR"
    assert log_json["msg"] == "Mensagem de teste ERROR"


def test_safe_json_dumps_datetime():
    from datetime import datetime
    dt = datetime(2024, 6, 1, 12, 0, 0)
    data = {"date": dt}
    json_str = safe_json_dumps(data)
    assert "2024-06-01T12:00:00" in json_str
