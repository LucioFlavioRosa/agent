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

# Novo teste para modo degradado
@pytest.mark.asyncio
def test_auth_without_key_vault_secrets(client):
    # Simula falha no carregamento de segredos do Key Vault
    with patch("backend.app.services.config_loader_service.ConfigLoaderService.load_secrets_from_key_vault") as mock_loader:
        mock_loader.side_effect = Exception("Key Vault indisponível")
        # O sistema deve entrar em modo degradado, endpoints críticos devem retornar erro 503
        response = client.get("/auth/config")
        # O endpoint pode retornar 503 ou 500 dependendo da implementação
        assert response.status_code in (503, 500)
        assert "detail" in response.json()
