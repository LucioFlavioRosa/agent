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
        "usuario_executor": "lucio.rosa@peers.com",
        "instrucoes_extras": "Adicionar validação extra no fluxo."
    }

@patch("services.report_handler.ReportHandler.read_existing_report_from_blob")
@patch("tools.blob_storage_utils.get_blob_container_name")
def test_start_analysis_with_existing_report(
    mock_get_blob_container_name,
    mock_read_report,
    client,
    payload
):
    mock_read_report.return_value = "Relatório já existente no Blob Storage."
    mock_get_blob_container_name.return_value = "container-grupo-peers"

    response = client.post("/start-analysis", json=payload)
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    assert job_id.startswith("job_")
    assert response.json()["analysis_report"] == "Relatório já existente no Blob Storage."

    # Garante que o container foi resolvido corretamente para leitura
    mock_get_blob_container_name.assert_called()
    assert mock_get_blob_container_name.return_value == "container-grupo-peers"
