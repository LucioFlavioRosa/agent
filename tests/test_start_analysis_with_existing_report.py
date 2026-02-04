import pytest
from fastapi.testclient import TestClient
from mcp_server_fastapi import app
from unittest.mock import patch, MagicMock

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def payload():
    return {
        "repository_type": "github",
        "repo_name": "org/projeto/repo",
        "branch_name": "main",
        "analysis_type": "melhoria_codigo",
        "usuario_executor": "lucio.rosa@peers.com"
    }

@patch("services.report_handler.ReportHandler.read_existing_report_from_blob")
@patch("services.simplified_workflow_service.SimplifiedWorkflowService.start_analysis")
def test_start_analysis_with_existing_report(mock_start_analysis, mock_read_report, client, payload):
    # Simula job_id gerado
    mock_start_analysis.return_value = "job_123"
    # Simula relatório existente no Blob Storage
    mock_read_report.return_value = "Relatório existente do Blob Storage."

    response = client.post("/start-analysis", json=payload)
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    assert job_id == "job_123"

    # Agora consulta o relatório
    with patch("services.simplified_workflow_service.SimplifiedWorkflowService.get_status") as mock_status:
        mock_status.return_value = {
            "job_id": job_id,
            "status": "completed",
            "report_url": f"http://localhost/reports/{job_id}",
            "analysis_report": "Relatório existente do Blob Storage."
        }
        status_response = client.get(f"/status/{job_id}")
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["analysis_report"] == "Relatório existente do Blob Storage."
        assert data["status"] == "completed"

    # Garante que nenhum processamento adicional foi realizado (workflow não foi chamado)
    # O start_analysis apenas registra o job, mas o relatório já existe
    mock_read_report.assert_called_once()
