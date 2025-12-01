import pytest
from unittest.mock import patch, MagicMock
from backend.app.core.config import settings

# Supondo que exista um ConfigLoaderService responsável por carregar segredos do Key Vault
class DummyConfigLoaderService:
    _cache = {}
    def __init__(self, secret_manager):
        self.secret_manager = secret_manager
    def load_secrets(self, secrets_map):
        # Simula cache: só busca do key vault se não estiver em _cache
        loaded = {}
        for key, vault_info in secrets_map.items():
            if key in self._cache:
                loaded[key] = self._cache[key]
            else:
                try:
                    value = self.secret_manager.get_secret(vault_info['secret_name'], vault_info['vault_url'])
                    loaded[key] = value
                    self._cache[key] = value
                except Exception:
                    loaded[key] = None
        return loaded

class DummySecretManager:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.calls = []
    def get_secret(self, secret_name, vault_url):
        self.calls.append((secret_name, vault_url))
        if self.should_fail:
            raise Exception("Key Vault failure")
        return f"mocked-{secret_name}-from-{vault_url}"

@pytest.fixture
def secrets_map():
    return {
        'AZURE_STORAGE_CONNECTION_STRING': {
            'secret_name': 'AZURE_STORAGE_CONNECTION_STRING',
            'vault_url': 'https://kv-codeai-azure-dev-usc.vault.azure.net/'
        },
        'AZURE_AD_CLIENT_SECRET': {
            'secret_name': 'AZURE_AD_CLIENT_SECRET',
            'vault_url': 'https://kv-codeai-azure-dev-usc.vault.azure.net/'
        },
        'DEVOPS_TOKEN': {
            'secret_name': 'DEVOPS_TOKEN',
            'vault_url': 'https://kv-codeai-devops-dev-usc.vault.azure.net/'
        }
    }

@pytest.mark.asyncio
def test_load_secrets_success(secrets_map):
    secret_manager = DummySecretManager()
    loader = DummyConfigLoaderService(secret_manager)
    loaded = loader.load_secrets(secrets_map)
    assert loaded['AZURE_STORAGE_CONNECTION_STRING'] == 'mocked-AZURE_STORAGE_CONNECTION_STRING-from-https://kv-codeai-azure-dev-usc.vault.azure.net/'
    assert loaded['DEVOPS_TOKEN'] == 'mocked-DEVOPS_TOKEN-from-https://kv-codeai-devops-dev-usc.vault.azure.net/'
    assert len(secret_manager.calls) == 3

@pytest.mark.asyncio
def test_update_settings_after_load(secrets_map):
    secret_manager = DummySecretManager()
    loader = DummyConfigLoaderService(secret_manager)
    loaded = loader.load_secrets(secrets_map)
    # Simula atualização do objeto settings
    settings.AZURE_STORAGE_CONNECTION_STRING = loaded['AZURE_STORAGE_CONNECTION_STRING']
    assert settings.AZURE_STORAGE_CONNECTION_STRING.startswith('mocked-AZURE_STORAGE_CONNECTION_STRING')

@pytest.mark.asyncio
def test_cache_behavior(secrets_map):
    secret_manager = DummySecretManager()
    loader = DummyConfigLoaderService(secret_manager)
    loader.load_secrets(secrets_map)
    # Segunda chamada não deve acessar o Key Vault novamente
    secret_manager.calls.clear()
    loader.load_secrets(secrets_map)
    assert len(secret_manager.calls) == 0

@pytest.mark.asyncio
def test_fallback_to_env_var_on_failure(secrets_map, monkeypatch):
    secret_manager = DummySecretManager(should_fail=True)
    loader = DummyConfigLoaderService(secret_manager)
    monkeypatch.setenv('AZURE_STORAGE_CONNECTION_STRING', 'env-connection-string')
    loaded = loader.load_secrets(secrets_map)
    # Simula fallback: se falhar, pega do env
    for key in loaded:
        if loaded[key] is None:
            loaded[key] = settings.__getattribute__(key) if hasattr(settings, key) else os.environ.get(key)
    assert loaded['AZURE_STORAGE_CONNECTION_STRING'] == 'env-connection-string'
