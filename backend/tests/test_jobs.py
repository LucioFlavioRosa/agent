import pytest
from fastapi.testclient import TestClient
from mcp_server_fastapi import app
import uuid

client = TestClient(app)

ANALYSIS_TYPE = "some_analysis_type"  # Substitua por um tipo válido do seu workflows.yaml

@pytest.fixture
def unique_analysis_name():
    return f"test-analysis-{uuid.uuid4().hex[:8]}"

def test_create_analysis_with_name(unique_analysis_name):
    payload = {
        "repo_name": "org/test-repo",
        "analysis_type": ANALYSIS_TYPE,
        "analysis_name": unique_analysis_name
    }
    response = client.post("/start-analysis", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["analysis_name"] == unique_analysis_name.lower()

def test_duplicate_analysis_name_rejected(unique_analysis_name):
    payload = {
        "repo_name": "org/test-repo",
        "analysis_type": ANALYSIS_TYPE,
        "analysis_name": unique_analysis_name
    }
    # Primeira criação
    response1 = client.post("/start-analysis", json=payload)
    assert response1.status_code == 200
    # Segunda tentativa com o mesmo nome
    response2 = client.post("/start-analysis", json=payload)
    assert response2.status_code == 409
    assert "análise com este nome" in response2.json()["detail"]

def test_get_report_by_analysis_name(unique_analysis_name):
    payload = {
        "repo_name": "org/test-repo",
        "analysis_type": ANALYSIS_TYPE,
        "analysis_name": unique_analysis_name
    }
    response = client.post("/start-analysis", json=payload)
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    # Simula conclusão do job e grava relatório
    from tools.job_store import RedisJobStore
    job_store = RedisJobStore()
    job = job_store.get_job(job_id)
    job["data"]["analysis_report"] = "Relatório de Teste"
    job_store.set_job(job_id, job)
    # Busca pelo endpoint tradicional
    report_response = client.get(f"/jobs/{job_id}/report")
    assert report_response.status_code == 200
    assert report_response.json()["analysis_report"] == "Relatório de Teste"
    # Busca pelo endpoint por nome
    report_by_name = client.get(f"/jobs/by-name/{unique_analysis_name}/report")
    assert report_by_name.status_code == 200
    assert report_by_name.json()["analysis_report"] == "Relatório de Teste"
    assert report_by_name.json()["analysis_name"] == unique_analysis_name.lower()

def test_get_report_by_job_id_and_no_name():
    payload = {
        "repo_name": "org/test-repo",
        "analysis_type": ANALYSIS_TYPE
    }
    response = client.post("/start-analysis", json=payload)
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    from tools.job_store import RedisJobStore
    job_store = RedisJobStore()
    job = job_store.get_job(job_id)
    job["data"]["analysis_report"] = "Relatório Sem Nome"
    job_store.set_job(job_id, job)
    report_response = client.get(f"/jobs/{job_id}/report")
    assert report_response.status_code == 200
    assert report_response.json()["analysis_report"] == "Relatório Sem Nome"
    assert report_response.json()["analysis_name"] is None
