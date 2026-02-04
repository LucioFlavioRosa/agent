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
@patch("services.report_handler.ReportHandler.save_report_to_blob")
@patch("services.simplified_workflow_service.SimplifiedWorkflowService.start_analysis")
@patch("tools.prompt_utils.carregar_prompt")
@patch("services.factories.llm_provider_factory.create_provider")
def test_start_analysis_without_existing_report(
    mock_create_provider,
    mock_carregar_prompt,
    mock_start_analysis,
    mock_save_report,
    mock_read_report,
    client,
    payload
):
    mock_start_analysis.return_value = "job_456"
    mock_read_report.return_value = None  # Não existe relatório
    mock_carregar_prompt.return_value = "Prompt base para melhoria de código."
    mock_save_report.return_value = "http://blobstorage/fake_report_url"

    # Simula provider LLM
    mock_llm = MagicMock()
    mock_llm.generate_report.return_value = "Relatório gerado pela LLM."
    mock_create_provider.return_value = mock_llm

    response = client.post("/start-analysis", json=payload)
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    assert job_id == "job_456"

    # Simula execução do workflow e geração do relatório
    with patch("services.simplified_workflow_service.SimplifiedWorkflowService.get_status") as mock_status:
        mock_status.return_value = {
            "job_id": job_id,
            "status": "completed",
            "report_url": "http://blobstorage/fake_report_url",
            "analysis_report": "Relatório gerado pela LLM."
        }
        status_response = client.get(f"/status/{job_id}")
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["analysis_report"] == "Relatório gerado pela LLM."
        assert data["report_url"] == "http://blobstorage/fake_report_url"
        assert data["status"] == "completed"

    # Garante que o prompt foi carregado e concatenado com instruções extras
    mock_carregar_prompt.assert_called_once_with("melhoria_codigo")
    mock_llm.generate_report.assert_called()
    mock_save_report.assert_called()
