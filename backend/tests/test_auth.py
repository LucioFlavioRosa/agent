import pytest
from fastapi.testclient import TestClient
from backend.main import app
from unittest.mock import patch

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture(autouse=True)
def mock_key_vault_secrets(monkeypatch):
    # Simula carregamento dos segredos do Key Vault antes dos testes
    with patch("backend.app.services.azure_secret_manager.AzureSecretManager.get_secret") as mock_get_secret:
        mock_get_secret.side_effect = lambda secret_name: f"mocked-{secret_name}-value"
        yield

# Exemplo de teste de autenticação
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

# Outros testes de autenticação podem ser adicionados aqui, usando o fixture mock_key_vault_secrets
