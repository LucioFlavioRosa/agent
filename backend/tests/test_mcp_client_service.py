import pytest
from unittest.mock import patch, Mock
from requests.exceptions import Timeout, HTTPError

# Supondo que MCPClientService esteja em backend/services/mcp_client_service.py
from backend.services.mcp_client_service import MCPClientService, MCPStartAnalysisResponse

@patch('backend.services.mcp_client_service.requests.post')
def test_start_analysis_success(mock_post):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"job_id": "abc-123"}
    mock_post.return_value = mock_response
    client = MCPClientService(base_url="https://mcp-server-endpoint")
    payload = {
        "analysis_type": "criacao_epicos_azure_devops",
        "instrucoes_extras": "texto extraido",
        "projeto": "projetoX",
        "analysis_name": "analise123",
        "usuario_executor": "usuario1"
    }
    with patch.object(client, 'get_mcp_endpoint', return_value="https://mcp-server-endpoint/start-analysis"):
        response = client.start_analysis(payload)
    assert isinstance(response, MCPStartAnalysisResponse)
    assert response.job_id == "abc-123"

@patch('backend.services.mcp_client_service.requests.post')
def test_start_analysis_http_error(mock_post):
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = HTTPError("Internal Server Error")
    mock_post.return_value = mock_response
    client = MCPClientService(base_url="https://mcp-server-endpoint")
    payload = {
        "analysis_type": "criacao_epicos_azure_devops",
        "instrucoes_extras": "texto extraido",
        "projeto": "projetoX",
        "analysis_name": "analise123",
        "usuario_executor": "usuario1"
    }
    with patch.object(client, 'get_mcp_endpoint', return_value="https://mcp-server-endpoint/start-analysis"):
        with pytest.raises(HTTPError):
            client.start_analysis(payload)

@patch('backend.services.mcp_client_service.requests.post', side_effect=Timeout)
def test_start_analysis_timeout(mock_post):
    client = MCPClientService(base_url="https://mcp-server-endpoint")
    payload = {
        "analysis_type": "criacao_epicos_azure_devops",
        "instrucoes_extras": "texto extraido",
        "projeto": "projetoX",
        "analysis_name": "analise123",
        "usuario_executor": "usuario1"
    }
    with patch.object(client, 'get_mcp_endpoint', return_value="https://mcp-server-endpoint/start-analysis"):
        with pytest.raises(Timeout):
            client.start_analysis(payload)

# Novos testes para get_mcp_endpoint
@pytest.mark.parametrize("analysis_type, expected_url", [
    ("criacao_epicos_azure_devops", "https://mcp-azure-devops-app-service/start-analysis"),
    ("analise_reuniao", "https://mcp-reuniao-app-service/start-analysis"),
    ("tipo_inexistente", "https://default-mcp-app-service/start-analysis")
])
def test_get_mcp_endpoint(analysis_type, expected_url):
    client = MCPClientService()
    # Simula mapeamento interno
    client._analysis_type_to_endpoint = {
        "criacao_epicos_azure_devops": "https://mcp-azure-devops-app-service/start-analysis",
        "analise_reuniao": "https://mcp-reuniao-app-service/start-analysis"
    }
    client._default_endpoint = "https://default-mcp-app-service/start-analysis"
    url = client.get_mcp_endpoint(analysis_type)
    assert url == expected_url
