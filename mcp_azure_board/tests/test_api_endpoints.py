import pytest
from fastapi.testclient import TestClient
from mcp_azure_board.mcp_server_fastapi import app

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

def test_start_analysis_criacao_epicos(client):
    payload = {
        "repo_name_modernizado": "org/proj/repo",
        "branch_name_modernizado": "main",
        "analysis_type": "criacao_epicos_azure_devops",
        "organization": "org",
        "project": "proj",
        "repository_type": "azure",
        "instrucoes_extras": "transcrição da reunião"
    }
    response = client.post("/start-analysis", json=payload)
    assert response.status_code == 200
    assert "job_id" in response.json()

def test_start_analysis_criacao_features(client):
    payload = {
        "repo_name_modernizado": "org/proj/repo",
        "branch_name_modernizado": "main",
        "analysis_type": "criacao_features_azure_devops",
        "epic_id": "12345",
        "organization": "org",
        "project": "proj",
        "repository_type": "azure",
        "instrucoes_extras": "relatório de features"
    }
    response = client.post("/start-analysis", json=payload)
    assert response.status_code == 200
    assert "job_id" in response.json()

def test_start_analysis_criacao_tarefas(client):
    payload = {
        "repo_name_modernizado": "org/proj/repo",
        "branch_name_modernizado": "main",
        "analysis_type": "criacao_tarefas_azure_devops",
        "feature_id": "54321",
        "organization": "org",
        "project": "proj",
        "repository_type": "azure",
        "instrucoes_extras": "relatório de tarefas"
    }
    response = client.post("/start-analysis", json=payload)
    assert response.status_code == 200
    assert "job_id" in response.json()

def test_start_analysis_revisor_tarefas(client):
    payload = {
        "repo_name_modernizado": "org/proj/repo",
        "branch_name_modernizado": "main",
        "analysis_type": "revisor_tarefas",
        "task_id": "67890",
        "organization": "org",
        "project": "proj",
        "repository_type": "azure",
        "instrucoes_extras": "relatório de revisão"
    }
    response = client.post("/start-analysis", json=payload)
    assert response.status_code == 200
    assert "job_id" in response.json()

def test_update_job_status(client):
    # Este teste depende de um job_id válido, normalmente obtido dos testes anteriores
    # Aqui, apenas estrutura para exemplo
    job_id = "job_id_exemplo"
    payload = {
        "job_id": job_id,
        "action": "approve",
        "instrucoes_extras": "Aprovado para execução"
    }
    response = client.post("/update-job-status", json=payload)
    assert response.status_code in (200, 400, 404)  # Pode falhar se job_id não existir

def test_get_job_report(client):
    job_id = "job_id_exemplo"
    response = client.get(f"/jobs/{job_id}/report")
    assert response.status_code in (200, 404)

def test_get_analysis_by_name(client):
    analysis_name = "analysis_name_exemplo"
    response = client.get(f"/analyses/by-name/{analysis_name}")
    assert response.status_code in (200, 404)
