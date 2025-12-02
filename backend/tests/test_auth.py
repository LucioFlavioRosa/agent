import pytest
from fastapi.testclient import TestClient
from backend.main import app
from unittest.mock import patch

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture(autouse=True)
def mock_key_vault_secrets(monkeypatch):
    def secret_side_effect(secret_name):
        if '-' in secret_name:
            return f"mocked-{secret_name}-value"
        elif '_' in secret_name:
            return f"mocked-env-{secret_name}-value"
        return f"mocked-{secret_name}-value"
    with patch("backend.app.services.azure_secret_manager.AzureSecretManager.get_secret") as mock_get_secret:
        mock_get_secret.side_effect = secret_side_effect
        yield

@pytest.mark.asyncio
def test_auth_config_endpoint(client):
    response = client.get("/auth/config")
    assert response.status_code == 200
    data = response.json()
    assert "client_id" in data
    assert "tenant_id" in data
    assert "authority" in data
    assert "redirect_uri" in data
    assert "scope" in data

@pytest.mark.asyncio
def test_auth_without_key_vault_secrets(client):
    with patch("backend.app.services.config_loader_service.ConfigLoaderService.load_secrets_from_key_vault") as mock_loader:
        mock_loader.side_effect = Exception("Key Vault indisponível")
        response = client.get("/auth/config")
        assert response.status_code in (503, 500)
        assert "detail" in response.json()

@pytest.mark.asyncio
def test_session_docx_files_field(client):
    session_id = "test-session-id"
    with patch("backend.app.services.redis_session_service.RedisSessionService.get_session") as mock_get_session:
        mock_get_session.return_value = type("SessionData", (), {
            "epicos_report": None,
            "features_report": None,
            "times_descricao_report": None,
            "alocacao_times_report": None,
            "premissas_riscos_report": None,
            "docx_files": ["https://blob/docx1.docx", "https://blob/docx2.docx"]
        })()
        response = client.get(f"/session/{session_id}/reports")
        assert response.status_code == 200
        data = response.json()
        assert "epicos_report" in data
        assert "features_report" in data
        assert "times_descricao_report" in data
        assert "alocacao_times_report" in data
        assert "premissas_riscos_report" in data
        response_files = client.get(f"/session/{session_id}/docx-files")
        assert response_files.status_code == 200
        files_data = response_files.json()
        assert "docx_files" in files_data
        assert isinstance(files_data["docx_files"], list)
        assert files_data["docx_files"] == ["https://blob/docx1.docx", "https://blob/docx2.docx"]
