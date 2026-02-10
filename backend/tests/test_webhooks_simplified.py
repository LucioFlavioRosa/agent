import pytest
from fastapi.testclient import TestClient
from backend.main import app
from unittest.mock import patch, MagicMock

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    # Mock RedisSessionService para não depender de Redis real
    from backend.app.services.redis_session_service import RedisSessionService
    mock_service = MagicMock()
    monkeypatch.setattr("backend.app.services.redis_session_service.RedisSessionService", lambda: mock_service)
    yield mock_service

@pytest.mark.asyncio
def test_webhook_mcp_done(client, mock_redis):
    payload = {
        "job_id": "job-uuid-456",
        "status": "done",
        "project_id": "projeto-uuid-123",
        "report_data": {"features_report": [{"id": 1, "nome": "Login"}]}
    }
    mock_redis.store_report_data_for_job.return_value = None
    mock_redis.update_job_status.return_value = None
    response = client.post("/webhooks/mcp", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["project_id"] == "projeto-uuid-123"
    mock_redis.store_report_data_for_job.assert_called_with("job-uuid-456", payload["report_data"])
    mock_redis.update_job_status.assert_called_with("job-uuid-456", "done")

@pytest.mark.asyncio
def test_webhook_mcp_error(client, mock_redis):
    payload = {
        "job_id": "job-uuid-456",
        "status": "error",
        "project_id": "projeto-uuid-123",
        "error_message": "Falha no processamento"
    }
    mock_redis.update_job_status.return_value = None
    response = client.post("/webhooks/mcp", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    mock_redis.update_job_status.assert_called_with("job-uuid-456", "error")

@pytest.mark.asyncio
def test_webhook_mcp_missing_fields(client, mock_redis):
    payload = {
        "status": "done",
        "report_data": {"features_report": [{"id": 1, "nome": "Login"}]}
    }
    response = client.post("/webhooks/mcp", json=payload)
    assert response.status_code == 400
    assert "Campos obrigatórios ausentes" in response.text
