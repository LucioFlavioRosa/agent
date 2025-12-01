import pytest
from unittest.mock import patch, MagicMock
from backend.app.services.azure_secret_manager import AzureSecretManager
from azure.keyvault.secrets import SecretClient

class DummySecret:
    def __init__(self, value):
        self.value = value

@pytest.fixture
def env_key_vault_url(monkeypatch):
    monkeypatch.setenv("KEY_VAULT_URL", "https://dummy-vault.vault.azure.net/")
    yield
    monkeypatch.delenv("KEY_VAULT_URL", raising=False)

@pytest.fixture
def env_key_vault_url_none(monkeypatch):
    monkeypatch.delenv("KEY_VAULT_URL", raising=False)
    yield

def test_initialization_with_vault_url(env_key_vault_url):
    manager = AzureSecretManager()
    assert manager._key_vault_url == "https://dummy-vault.vault.azure.net/"
    assert manager._secret_client is None

def test_initialization_without_vault_url(env_key_vault_url_none):
    with pytest.raises(EnvironmentError):
        AzureSecretManager()

@patch("backend.app.services.azure_secret_manager.SecretClient")
def test_get_secret_success(mock_secret_client, env_key_vault_url):
    manager = AzureSecretManager()
    dummy_client = MagicMock()
    dummy_client.get_secret.return_value = DummySecret("super-secret-value")
    manager._secret_client = dummy_client
    secret_value = manager.get_secret("MY_SECRET")
    assert secret_value == "super-secret-value"
    dummy_client.get_secret.assert_called_once_with("MY_SECRET")

@patch("backend.app.services.azure_secret_manager.SecretClient")
def test_get_secret_empty_value(mock_secret_client, env_key_vault_url):
    manager = AzureSecretManager()
    dummy_client = MagicMock()
    dummy_client.get_secret.return_value = DummySecret("")
    manager._secret_client = dummy_client
    with pytest.raises(ValueError):
        manager.get_secret("EMPTY_SECRET")

@patch("backend.app.services.azure_secret_manager.SecretClient")
def test_get_secret_exception(mock_secret_client, env_key_vault_url):
    manager = AzureSecretManager()
    dummy_client = MagicMock()
    dummy_client.get_secret.side_effect = Exception("fail")
    manager._secret_client = dummy_client
    with pytest.raises(ValueError):
        manager.get_secret("FAIL_SECRET")

@patch("backend.app.services.azure_secret_manager.SecretClient")
def test_client_cache(mock_secret_client, env_key_vault_url):
    manager = AzureSecretManager()
    # Força _secret_client=None para testar cache
    manager._secret_client = None
    with patch("backend.app.services.azure_secret_manager.DefaultAzureCredential") as mock_cred:
        mock_client_instance = MagicMock()
        mock_secret_client.return_value = mock_client_instance
        client1 = manager._get_secret_client()
        client2 = manager._get_secret_client()
        assert client1 is client2
        mock_secret_client.assert_called_once_with(vault_url=manager._key_vault_url, credential=mock_cred.return_value)
