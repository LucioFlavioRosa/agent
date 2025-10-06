import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, call
import uuid
from mcp_server_fastapi import app
from models import JobFields, JobActions, JobStatus

client = TestClient(app)

# Utilitário para gerar payload válido
VALID_PAYLOAD = {
    "repo_name_modernizado": "repo-exemplo",
    "branch_name_modernizado": "main",
    "projeto": "projeto-teste",
    "analysis_type": "modernizacao",  # Supondo que 'modernizacao' seja válido
    "repository_type": "github"
}

def test_start_analysis_with_invalid_repository_type():
    payload = VALID_PAYLOAD.copy()
    payload["repository_type"] = "bitbucket"  # Valor inválido
    response = client.post("/start-analysis", json=payload)
    assert response.status_code == 422
    assert "repository_type" in response.text

@patch("mcp_server_fastapi.container.get_job_store")
@patch("mcp_server_fastapi.container.get_analysis_name_service")
@patch("mcp_server_fastapi.api_service_factory.get_repository_normalizer_service")
@patch("mcp_server_fastapi.api_service_factory.get_job_data_service")
@patch("mcp_server_fastapi.api_service_factory.get_logging_service")
def test_start_analysis_creates_job_and_returns_job_id(mock_logging_service, mock_job_data_service, mock_repository_normalizer_service, mock_analysis_service, mock_job_store):
    # Arrange
    mock_job_store.return_value = MagicMock()
    mock_analysis_service.return_value = MagicMock()
    mock_repository_normalizer_service.return_value.normalize_repo_name.return_value = "repo-normalizado"
    mock_job_data_service.return_value.generate_analysis_name.return_value = "analysis-123"
    mock_job_data_service.return_value.create_initial_job_data.return_value = {"dummy": "data", "data": {"analysis_type": "modernizacao"}}
    mock_logging_service.return_value = MagicMock()
    payload = VALID_PAYLOAD.copy()
    payload["analysis_type"] = "modernizacao"
    with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
        response = client.post("/start-analysis", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["job_id"] == "12345678-1234-5678-1234-567812345678"
    # Verifica se job_store.set_job foi chamado
    assert mock_job_store.return_value.set_job.called
    # Verifica se analysis_service.register_analysis foi chamado
    assert mock_analysis_service.return_value.register_analysis.called

@patch("mcp_server_fastapi.container.get_job_store")
@patch("mcp_server_fastapi.api_service_factory.get_job_validation_service")
def test_update_job_status_approve_with_paused_step(mock_job_validation_service, mock_job_store):
    mock_job_store.return_value = MagicMock()
    mock_job = {
        JobFields.DATA: {JobFields.PAUSED_AT_STEP: 2},
        JobFields.STATUS: "pending_approval"
    }
    mock_job_store.return_value.get_job.return_value = mock_job
    mock_job_validation_service.return_value.validate_job_for_approval.return_value = None
    payload = {
        "job_id": "job-123",
        "action": "approve"
    }
    with patch("mcp_server_fastapi.run_workflow_task") as mock_run_workflow_task:
        with patch("mcp_server_fastapi.BackgroundTasks.add_task") as mock_add_task:
            response = client.post("/update-job-status", json=payload)
            assert response.status_code == 200
            # O step deve ser PAUSED_AT_STEP + 1
            assert mock_add_task.call_args[0][1] == "job-123"
            assert mock_add_task.call_args[0][2] == 3

@patch("mcp_server_fastapi.container.get_job_store")
@patch("mcp_server_fastapi.api_service_factory.get_job_validation_service")
def test_update_job_status_reject_updates_status_to_rejected(mock_job_validation_service, mock_job_store):
    mock_job_store.return_value = MagicMock()
    mock_job = {
        JobFields.DATA: {},
        JobFields.STATUS: "pending_approval"
    }
    mock_job_store.return_value.get_job.return_value = mock_job
    payload = {
        "job_id": "job-456",
        "action": "reject"
    }
    with patch("mcp_server_fastapi.BackgroundTasks.add_task") as mock_add_task:
        response = client.post("/update-job-status", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == JobStatus.REJECTED
        # Não deve chamar add_task para rejeição
        assert not mock_add_task.called

@patch("mcp_server_fastapi.container.get_job_store")
@patch("mcp_server_fastapi.api_service_factory.get_job_validation_service")
def test_get_job_report_with_nonexistent_job_id(mock_job_validation_service, mock_job_store):
    mock_job_store.return_value = MagicMock()
    mock_job_store.return_value.get_job.return_value = None
    mock_job_validation_service.return_value.validate_job_exists.side_effect = Exception("Job not found")
    response = client.get("/jobs/nonexistent-job/report")
    assert response.status_code == 500 or response.status_code == 404
    assert "Job not found" in response.text

@patch("mcp_server_fastapi.container.get_job_store")
@patch("mcp_server_fastapi.container.get_analysis_name_service")
@patch("mcp_server_fastapi.api_service_factory.get_job_validation_service")
def test_get_analysis_by_name_with_invalid_analysis_name(mock_job_validation_service, mock_analysis_service, mock_job_store):
    mock_analysis_service.return_value = MagicMock()
    mock_job_validation_service.return_value.validate_analysis_exists.side_effect = Exception("Analysis not found")
    response = client.get("/analyses/by-name/invalid-analysis")
    assert response.status_code == 500 or response.status_code == 404
    assert "Analysis not found" in response.text

@patch("mcp_server_fastapi.container.get_job_store")
@patch("mcp_server_fastapi.container.get_analysis_name_service")
@patch("mcp_server_fastapi.api_service_factory.get_job_data_service")
@patch("mcp_server_fastapi.api_service_factory.get_repository_normalizer_service")
@patch("mcp_server_fastapi.api_service_factory.get_job_validation_service")
def test_start_code_generation_from_report_creates_derived_job(mock_job_validation_service, mock_repository_normalizer_service, mock_job_data_service, mock_analysis_service, mock_job_store):
    mock_job_store.return_value = MagicMock()
    mock_analysis_service.return_value = MagicMock()
    mock_job_validation_service.return_value.validate_analysis_exists.return_value = "job-789"
    mock_job_store.return_value.get_job.return_value = {
        JobFields.DATA: {
            JobFields.REPO_NAME: "repo-orig",
            JobFields.REPOSITORY_TYPE: "github",
            JobFields.PROJETO: "proj-teste"
        }
    }
    mock_repository_normalizer_service.return_value.normalize_repo_name.return_value = "repo-normalizado"
    mock_job_data_service.return_value.create_derived_job_data.return_value = {"dummy": "data", "data": {}}
    with patch("uuid.uuid4", return_value=uuid.UUID("87654321-4321-8765-4321-876543218765")):
        response = client.post("/start-code-generation-from-report/analysis-xyz")
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["job_id"] == "87654321-4321-8765-4321-876543218765"
    assert mock_job_store.return_value.set_job.called
    assert mock_analysis_service.return_value.register_analysis.called

@patch("mcp_server_fastapi.container.get_job_store")
@patch("mcp_server_fastapi.api_service_factory.get_response_builder_service")
def test_get_status_returns_completed_response_with_report_blob_url(mock_response_builder_service, mock_job_store):
    mock_job_store.return_value = MagicMock()
    job_id = "job-999"
    job = {
        JobFields.STATUS: JobStatus.COMPLETED,
        JobFields.DATA: {
            JobFields.REPORT_BLOB_URL: "https://blob.url/report.md"
        }
    }
    mock_job_store.return_value.get_job.return_value = job
    mock_response_builder_service.return_value.build_completed_response.return_value = {
        "job_id": job_id,
        "status": JobStatus.COMPLETED,
        "report_blob_url": "https://blob.url/report.md"
    }
    response = client.get(f"/status/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == JobStatus.COMPLETED
    assert data["report_blob_url"] == "https://blob.url/report.md"
    assert mock_response_builder_service.return_value.build_completed_response.called
