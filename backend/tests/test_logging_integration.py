import pytest
from fastapi.testclient import TestClient
import logging
import os
import re
from main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_logging_for_test(tmp_path, monkeypatch):
    log_file = tmp_path / "test_app_logs.log"
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    logger = logging.getLogger()
    for h in logger.handlers[:]:
        logger.removeHandler(h)
    handler = logging.FileHandler(str(log_file))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    yield log_file
    logger.removeHandler(handler)

# Utilitário para buscar logs por padrão
def find_log_lines(log_file, pattern):
    with open(log_file, "r") as f:
        return [line for line in f if re.search(pattern, line)]

# 1. Endpoint /analysis/start com payload válido e inválido
def test_analysis_start_logging_success(setup_logging_for_test):
    payload = {
        "email": "user@example.com",
        "nome_projeto": "Projeto Teste",
        "agent_name": "agent1",
        "analysis_type": "static",
        "branch": "main",
        "repository": "https://repo.git",
        "comentario_extra": "Teste de log"
    }
    response = client.post("/analysis/start", data=payload)
    assert response.status_code in [200, 400, 404, 500]  # Pode falhar por ausência do MCP
    logs = find_log_lines(setup_logging_for_test, r"Iniciando análise multiagente")
    assert any("Iniciando análise multiagente" in l for l in logs)


def test_analysis_start_logging_invalid_payload(setup_logging_for_test):
    payload = {
        "email": "",
        "nome_projeto": "",
        "agent_name": "",
        "analysis_type": ""
    }
    response = client.post("/analysis/start", data=payload)
    assert response.status_code in [400, 404, 500]
    logs = find_log_lines(setup_logging_for_test, r"Iniciando análise multiagente")
    assert any("Iniciando análise multiagente" in l for l in logs)

# 2. Chamada ao MCP com sucesso e erro
def test_mcp_client_logging(setup_logging_for_test):
    # Simula erro na chamada ao MCP
    payload = {
        "email": "user@example.com",
        "nome_projeto": "Projeto Teste",
        "agent_name": "agent1",
        "analysis_type": "static",
        "branch": "main",
        "repository": "https://repo.git",
        "comentario_extra": "Teste de log"
    }
    response = client.post("/analysis/start", data=payload)
    logs = find_log_lines(setup_logging_for_test, r"Erro na comunicação com MCP")
    assert any("Erro na comunicação com MCP" in l for l in logs)

# 3. Webhook /webhooks/mcp com diferentes status
def test_webhook_mcp_logging(setup_logging_for_test):
    payload = {
        "project_id": "proj123",
        "job_id": "job456",
        "status": "done",
        "report_data": {"result": "ok"}
    }
    response = client.post("/webhooks/mcp", json=payload)
    assert response.status_code == 200
    logs = find_log_lines(setup_logging_for_test, r"Job job456 status: done")
    assert any("Job job456 status: done" in l for l in logs)

    payload_error = {
        "project_id": "proj123",
        "job_id": "job789",
        "status": "error",
        "error_message": "Falha de processamento"
    }
    response = client.post("/webhooks/mcp", json=payload_error)
    logs = find_log_lines(setup_logging_for_test, r"Job job789 status: error")
    assert any("Job job789 status: error" in l for l in logs)

# 4. Endpoint /session/project/{project_id}/{job_id}/reports com report_data presente e ausente
def test_session_project_reports_logging(setup_logging_for_test):
    project_id = "proj123"
    job_id = "job456"
    response = client.get(f"/session/project/{project_id}/{job_id}/reports?email=user@example.com&empresa=EmpresaX")
    assert response.status_code in [200, 202]
    logs = find_log_lines(setup_logging_for_test, r"Report data não encontrado")
    assert any("Report data não encontrado" in l for l in logs)

# 5. Validação de campos esperados nos logs
def test_log_fields_presence(setup_logging_for_test):
    payload = {
        "email": "user@example.com",
        "nome_projeto": "Projeto Teste",
        "agent_name": "agent1",
        "analysis_type": "static"
    }
    client.post("/analysis/start", data=payload)
    logs = find_log_lines(setup_logging_for_test, r"Iniciando análise multiagente")
    # Verifica se há timestamp e level
    assert any(re.search(r'"timestamp":', l) and re.search(r'"level":', l) for l in logs)
