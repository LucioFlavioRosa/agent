import pytest
from fastapi.testclient import TestClient
from mcp_server_fastapi import app, job_store
import uuid

client = TestClient(app)

ANALYSIS_NAME = f"test-analysis-{uuid.uuid4()}"

# Mock payload para criação de análise
def get_payload():
    return {
        "repo_name": "org/testrepo",
        "analysis_type": "default", # ajuste conforme workflow
        "branch_name": "main",
        "instrucoes_extras": "Teste de nomeação de análise.",
        "usar_rag": False,
        "gerar_relatorio_apenas": True,
        "model_name": None,
        "analysis_name": ANALYSIS_NAME
    }

# Teste: Criação de análise com nome
def test_create_analysis_with_name():
    response = client.post("/start-analysis", json=get_payload())
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    job = job_store.get_job(job_id)
    assert job is not None
    assert job["data"].get("analysis_name") == ANALYSIS_NAME

# Teste: Recuperação de relatório por nome
def test_retrieve_report_by_analysis_name():
    # Cria análise
    response = client.post("/start-analysis", json=get_payload())
    job_id = response.json()["job_id"]
    # Aguarda processamento
    import time; time.sleep(2)
    # Busca relatório por nome
    response2 = client.get(f"/analyses/by-name/{ANALYSIS_NAME}")
    assert response2.status_code == 200
    data = response2.json()
    assert data["job_id"] == job_id
    assert data["analysis_name"] == ANALYSIS_NAME
    assert "analysis_report" in data

# Teste: Geração de código a partir de relatório existente
def test_code_generation_from_existing_report():
    # Cria análise
    response = client.post("/start-analysis", json=get_payload())
    job_id = response.json()["job_id"]
    import time; time.sleep(2)
    # Inicia geração de código a partir do relatório
    response2 = client.post(f"/start-code-generation-from-report/{ANALYSIS_NAME}")
    assert response2.status_code == 200
    assert "job_id" in response2.json()

# Teste: Nomes duplicados (política: sobrescrita)
def test_duplicate_analysis_name_overwrites():
    payload = get_payload()
    response1 = client.post("/start-analysis", json=payload)
    job_id1 = response1.json()["job_id"]
    # Cria nova análise com mesmo nome
    response2 = client.post("/start-analysis", json=payload)
    job_id2 = response2.json()["job_id"]
    assert job_id1 != job_id2
    # Busca pelo nome deve retornar o último job_id
    response3 = client.get(f"/analyses/by-name/{ANALYSIS_NAME}")
    assert response3.status_code == 200
    assert response3.json()["job_id"] == job_id2
