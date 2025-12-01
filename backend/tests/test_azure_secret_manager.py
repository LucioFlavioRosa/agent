import pytest
from unittest.mock import patch, MagicMock
from backend.app.services.azure_secret_manager import AzureSecretManager
from azure.keyvault.secrets import SecretClient
import os

class DummySecret:
    def __init__(self, value):
        self.value = value

@pytest.fixture(params=["AZURE_KV_URL", "DEVOPS_KV_URL", "GITHUB_KV_URL", "LLM_KV_URL"])
def env_key_vault_url(monkeypatch, request):
    monkeypatch.setenv(request.param, f"https://dummy-{request.param.lower()}.vault.azure.net/")
    yield request.param
    monkeypatch.delenv(request.param, raising=False)

@pytest.fixture(params=["AZURE_KV_URL", "DEVOPS_KV_URL", "GITHUB_KV_URL", "LLM_KV_URL"])
def env_key_vault_url_none(monkeypatch, request):
    monkeypatch.delenv(request.param, raising=False)
    yield request.param

# Testa inicialização para cada tipo de vault usando variável de ambiente
@pytest.mark.parametrize("vault_type, env_var", [
    ("azure", "AZURE_KV_URL"),
    ("devops", "DEVOPS_KV_URL"),
    ("github", "GITHUB_KV_URL"),
    ("llm", "LLM_KV_URL")
])
def test_initialization_with_vault_url(monkeypatch, vault_type, env_var):
    url = f"https://dummy-{env_var.lower()}.vault.azure.net/"
    monkeypatch.setenv(env_var, url)
    manager = AzureSecretManager(vault_type)
    assert manager._key_vault_url == url
    assert manager._secret_client is None
    monkeypatch.delenv(env_var, raising=False)

@pytest.mark.parametrize("vault_type, env_var", [
    ("azure", "AZURE_KV_URL"),
    ("devops", "DEVOPS_KV_URL"),
    ("github", "GITHUB_KV_URL"),
    ("llm", "LLM_KV_URL")
])
def test_initialization_without_vault_url(monkeypatch, vault_type, env_var):
    monkeypatch.delenv(env_var, raising=False)
    with pytest.raises(EnvironmentError):
        AzureSecretManager(vault_type)

@patch("backend.app.services.azure_secret_manager.SecretClient")
def test_get_secret_success(mock_secret_client, monkeypatch):
    monkeypatch.setenv("AZURE_KV_URL", "https://dummy-azure.vault.azure.net/")
    manager = AzureSecretManager("azure")
    dummy_client = MagicMock()
    dummy_client.get_secret.return_value = DummySecret("super-secret-value")
    manager._secret_client = dummy_client
    secret_value = manager.get_secret("MY_SECRET")
    assert secret_value == "super-secret-value"
    dummy_client.get_secret.assert_called_once_with("MY_SECRET")
    monkeypatch.delenv("AZURE_KV_URL", raising=False)

@patch("backend.app.services.azure_secret_manager.SecretClient")
def test_get_secret_empty_value(mock_secret_client, monkeypatch):
    monkeypatch.setenv("AZURE_KV_URL", "https://dummy-azure.vault.azure.net/")
    manager = AzureSecretManager("azure")
    dummy_client = MagicMock()
    dummy_client.get_secret.return_value = DummySecret("")
    manager._secret_client = dummy_client
    with pytest.raises(ValueError):
        manager.get_secret("EMPTY_SECRET")
    monkeypatch.delenv("AZURE_KV_URL", raising=False)

@patch("backend.app.services.azure_secret_manager.SecretClient")
def test_get_secret_exception(mock_secret_client, monkeypatch):
    monkeypatch.setenv("AZURE_KV_URL", "https://dummy-azure.vault.azure.net/")
    manager = AzureSecretManager("azure")
    dummy_client = MagicMock()
    dummy_client.get_secret.side_effect = Exception("fail")
    manager._secret_client = dummy_client
    with pytest.raises(ValueError):
        manager.get_secret("FAIL_SECRET")
    monkeypatch.delenv("AZURE_KV_URL", raising=False)

@patch("backend.app.services.azure_secret_manager.SecretClient")
def test_client_cache(mock_secret_client, monkeypatch):
    monkeypatch.setenv("AZURE_KV_URL", "https://dummy-azure.vault.azure.net/")
    manager = AzureSecretManager("azure")
    manager._secret_client = None
    with patch("backend.app.services.azure_secret_manager.DefaultAzureCredential") as mock_cred:
        mock_client_instance = MagicMock()
        mock_secret_client.return_value = mock_client_instance
        client1 = manager._get_secret_client()
        client2 = manager._get_secret_client()
        assert client1 is client2
        mock_secret_client.assert_called_once_with(vault_url=manager._key_vault_url, credential=mock_cred.return_value)
    monkeypatch.delenv("AZURE_KV_URL", raising=False)
