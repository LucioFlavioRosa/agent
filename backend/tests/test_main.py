import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from backend.app.main import app

@pytest.fixture
def client():
    return TestClient(app)

@patch("backend.app.main.vault_service")
@patch("backend.app.main.BlobServiceClient")
@patch("backend.app.main.QueueClient")
def test_start_analysis_endpoint_success(queue_client_mock, blob_service_client_mock, vault_service_mock, client):
    # Setup mocks
    vault_service_mock.get_secret = AsyncMock(side_effect=["blob_conn_str", "blob_container"])
    vault_service_mock.get_queue_connection_string = AsyncMock(return_value="queue_conn_str")
    blob_service_client_instance = MagicMock()
    blob_service_client_mock.from_connection_string.return_value = blob_service_client_instance
    container_client = MagicMock()
    blob_service_client_instance.get_container_client.return_value = container_client
    container_client.exists = AsyncMock(return_value=True)
    blob_client = MagicMock()
    container_client.get_blob_client.return_value = blob_client
    blob_client.upload_blob = AsyncMock()
    queue_client_instance = MagicMock()
    queue_client_mock.from_connection_string.return_value = queue_client_instance
    queue_client_instance.send_message = AsyncMock()

    data = {
        "job_id": "job123",
        "project_id": "proj456",
        "company_id": "comp789",
        "group_ids": "group1",
        "email": "user@example.com",
        "nome_projeto": "Projeto Teste",
        "analysis_type": "agent_epics_generator_digital",
        "branch": "main",
        "repository": "repo.git",
        "comentario_extra": "Comentario extra"
    }
    files = {"arquivo_docx": ("documento.docx", b"conteudo_docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    response = client.post("/api/v1/analysis/start", data=data, files=files)
    assert response.status_code == 202
    assert response.json()["job_id"] == "job123"
    assert response.json()["status"] == "queued"

@patch("backend.app.main.vault_service")
@patch("backend.app.main.BlobServiceClient")
@patch("backend.app.main.QueueClient")
def test_start_analysis_endpoint_missing_blob_creds(queue_client_mock, blob_service_client_mock, vault_service_mock, client):
    # Setup mocks for missing blob credentials
    vault_service_mock.get_secret = AsyncMock(side_effect=[None, None])
    response = client.post("/api/v1/analysis/start", data={
        "job_id": "job123",
        "project_id": "proj456",
        "company_id": "comp789"
    })
    assert response.status_code == 500
    assert "Falha de credenciais do Blob Storage" in response.json()["error"]

@patch("backend.app.main.vault_service")
@patch("backend.app.main.BlobServiceClient")
@patch("backend.app.main.QueueClient")
def test_start_analysis_endpoint_invalid_analysis_type(queue_client_mock, blob_service_client_mock, vault_service_mock, client):
    vault_service_mock.get_secret = AsyncMock(side_effect=["blob_conn_str", "blob_container"])
    vault_service_mock.get_queue_connection_string = AsyncMock(return_value="queue_conn_str")
    response = client.post("/api/v1/analysis/start", data={
        "job_id": "job123",
        "project_id": "proj456",
        "company_id": "comp789",
        "analysis_type": "invalid_type"
    })
    assert response.status_code == 500 or response.status_code == 400
    # O endpoint deve validar analysis_type e retornar erro
