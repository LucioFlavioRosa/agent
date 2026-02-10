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
def test_webhook_mcp_in_progress(client, mock_redis):
    payload = {
        "job_id": "job-uuid-456",
        "status": "in_progress",
        "project_id": "projeto-uuid-123"
    }
    mock_redis.update_job_status.return_value = None
    response = client.post("/webhooks/mcp", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "in_progress" in response.json()["msg"]
    mock_redis.update_job_status.assert_called_with("job-uuid-456", "in_progress")

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
    assert "error" in response.json()["msg"]
    mock_redis.update_job_status.assert_called_with("job-uuid-456", "error")

@pytest.mark.asyncio
def test_webhook_mcp_done(client, mock_redis):
    payload = {
        "job_id": "job-uuid-456",
        "status": "done",
        "project_id": "projeto-uuid-123",
        "report_data": {"features_report": [{"id": 1, "nome": "Login"}]}
    }
    mock_redis.update_report.return_value = None
    mock_redis.get_session_by_project_id.return_value = {"project_id": "projeto-uuid-123"}
    mock_redis.update_job_status.return_value = None
    response = client.post("/webhooks/mcp", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["project_id"] == "projeto-uuid-123"
    mock_redis.update_report.assert_called_with("projeto-uuid-123", payload["report_data"])
    mock_redis.update_job_status.assert_called_with("job-uuid-456", "done")
