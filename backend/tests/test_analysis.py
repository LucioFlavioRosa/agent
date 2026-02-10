import pytest
from fastapi.testclient import TestClient
from backend.main import app
from unittest.mock import patch, MagicMock

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture(autouse=True)
def mock_mongodb(monkeypatch):
    # Mock MongoDBService para não depender de Mongo real
    from backend.app.services.mongodb_service import MongoDBService
    mock_service = MagicMock()
    monkeypatch.setattr("backend.app.services.mongodb_service.MongoDBService", lambda: mock_service)
    yield mock_service

def test_post_analysis_start_valid(client, mock_mongodb):
    # Usuário com permissão e agente permitido
    mock_mongodb.get_user_by_email.return_value = {
        "email": "joao.silva@empresa.com",
        "active": True,
        "group_ids": ["group-devs-id"]
    }
    mock_mongodb.get_group_by_id.return_value = {
        "allowed_agents": ["agent_code_generation"]
    }
    mock_mongodb.get_project_by_id.return_value = {
        "_id": "project-id-555",
        "members": [{"email": "joao.silva@empresa.com", "role": "owner"}]
    }
    payload = {
        "email": "joao.silva@empresa.com",
        "nome_projeto": "Migração Legacy SAP",
        "agent_name": "agent_code_generation",
        "analysis_name": "code_generation",
        "branch_name": "main",
        "repository_name": "repo-sap",
        "instrucoes_extras": "Gerar código base"
    }
    response = client.post("/analysis/start", json=payload)
    assert response.status_code == 200
    assert "project_id" in response.json()
    assert "job_id" in response.json()


def test_post_analysis_start_no_permission(client, mock_mongodb):
    # Usuário sem permissão no projeto
    mock_mongodb.get_user_by_email.return_value = {
        "email": "maria@empresa.com",
        "active": True,
        "group_ids": ["group-devs-id"]
    }
    mock_mongodb.get_group_by_id.return_value = {
        "allowed_agents": ["agent_code_generation"]
    }
    mock_mongodb.get_project_by_id.return_value = {
        "_id": "project-id-555",
        "members": [{"email": "joao.silva@empresa.com", "role": "owner"}]
    }
    payload = {
        "email": "maria@empresa.com",
        "nome_projeto": "Migração Legacy SAP",
        "agent_name": "agent_code_generation",
        "analysis_name": "code_generation",
        "branch_name": "main",
        "repository_name": "repo-sap",
        "instrucoes_extras": "Gerar código base"
    }
    response = client.post("/analysis/start", json=payload)
    assert response.status_code == 403


def test_post_analysis_start_agent_not_allowed(client, mock_mongodb):
    # Agente não permitido para o grupo
    mock_mongodb.get_user_by_email.return_value = {
        "email": "joao.silva@empresa.com",
        "active": True,
        "group_ids": ["group-devs-id"]
    }
    mock_mongodb.get_group_by_id.return_value = {
        "allowed_agents": ["agent_refactoring"]
    }
    mock_mongodb.get_project_by_id.return_value = {
        "_id": "project-id-555",
        "members": [{"email": "joao.silva@empresa.com", "role": "owner"}]
    }
    payload = {
        "email": "joao.silva@empresa.com",
        "nome_projeto": "Migração Legacy SAP",
        "agent_name": "agent_code_generation",
        "analysis_name": "code_generation",
        "branch_name": "main",
        "repository_name": "repo-sap",
        "instrucoes_extras": "Gerar código base"
    }
    response = client.post("/analysis/start", json=payload)
    assert response.status_code == 403


def test_post_analysis_start_missing_fields(client, mock_mongodb):
    # Payload sem campos obrigatórios
    payload = {
        "email": "joao.silva@empresa.com",
        "nome_projeto": "Migração Legacy SAP"
    }
    response = client.post("/analysis/start", json=payload)
    assert response.status_code == 400
