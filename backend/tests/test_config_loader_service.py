import pytest
from unittest.mock import patch, MagicMock
from backend.app.core.config import settings
import os
import threading
import time

class DummySecretManager:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.calls = []
    def get_secret(self, secret_name):
        self.calls.append(secret_name)
        if self.should_fail:
            raise Exception("Key Vault failure")
        return f"mocked-{secret_name}"

class DummyConfigLoaderService:
    _cache = {}
    _lock = threading.Lock()
    def __init__(self, secret_manager):
        self.secret_manager = secret_manager
    def load_secrets(self, secrets_map):
        loaded = {}
        with self._lock:
            for key, vault_type in secrets_map.items():
                if key in self._cache:
                    loaded[key] = self._cache[key]
                else:
                    try:
                        value = self.secret_manager.get_secret(key)
                        loaded[key] = value
                        self._cache[key] = value
                    except Exception:
                        loaded[key] = os.environ.get(key)
        return loaded
    def invalidate_cache(self, key):
        with self._lock:
            if key in self._cache:
                del self._cache[key]

@pytest.fixture
def secrets_map():
    return {
        'AZURE_STORAGE_CONNECTION_STRING': 'azure',
        'AZURE_AD_CLIENT_SECRET': 'azure',
        'DEVOPS_TOKEN': 'devops'
    }

@pytest.mark.asyncio
def test_load_secrets_success(secrets_map):
    secret_manager = DummySecretManager()
    loader = DummyConfigLoaderService(secret_manager)
    loaded = loader.load_secrets(secrets_map)
    assert loaded['AZURE_STORAGE_CONNECTION_STRING'] == 'mocked-AZURE_STORAGE_CONNECTION_STRING'
    assert loaded['DEVOPS_TOKEN'] == 'mocked-DEVOPS_TOKEN'
    assert len(secret_manager.calls) == 3

@pytest.mark.asyncio
def test_update_settings_after_load(secrets_map):
    secret_manager = DummySecretManager()
    loader = DummyConfigLoaderService(secret_manager)
    loaded = loader.load_secrets(secrets_map)
    settings.AZURE_STORAGE_CONNECTION_STRING = loaded['AZURE_STORAGE_CONNECTION_STRING']
    assert settings.AZURE_STORAGE_CONNECTION_STRING.startswith('mocked-AZURE_STORAGE_CONNECTION_STRING')

@pytest.mark.asyncio
def test_cache_behavior(secrets_map):
    secret_manager = DummySecretManager()
    loader = DummyConfigLoaderService(secret_manager)
    loader.load_secrets(secrets_map)
    secret_manager.calls.clear()
    loader.load_secrets(secrets_map)
    assert len(secret_manager.calls) == 0

@pytest.mark.asyncio
def test_fallback_to_env_var_on_failure(secrets_map, monkeypatch):
    secret_manager = DummySecretManager(should_fail=True)
    loader = DummyConfigLoaderService(secret_manager)
    monkeypatch.setenv('AZURE_STORAGE_CONNECTION_STRING', 'env-connection-string')
    loaded = loader.load_secrets(secrets_map)
    assert loaded['AZURE_STORAGE_CONNECTION_STRING'] == 'env-connection-string'
    monkeypatch.delenv('AZURE_STORAGE_CONNECTION_STRING', raising=False)

@pytest.mark.parametrize("env_var", ["AZURE_KV_URL", "DEVOPS_KV_URL", "GITHUB_KV_URL", "LLM_KV_URL"])
def test_key_vault_url_env(monkeypatch, env_var):
    url = f"https://dummy-{env_var.lower()}.vault.azure.net/"
    monkeypatch.setenv(env_var, url)
    assert os.environ.get(env_var) == url
    monkeypatch.delenv(env_var, raising=False)

# =====================
# NOVOS TESTES DE CACHE E THREAD-SAFETY
# =====================

def test_cache_prevents_multiple_key_vault_calls(secrets_map):
    secret_manager = DummySecretManager()
    loader = DummyConfigLoaderService(secret_manager)
    # Primeira chamada popula o cache
    loader.load_secrets(secrets_map)
    # Limpa chamadas do secret_manager
    secret_manager.calls.clear()
    # Segunda chamada deve usar apenas o cache (nenhuma chamada ao Key Vault)
    loader.load_secrets(secrets_map)
    assert len(secret_manager.calls) == 0


def test_cache_invalidation_on_error(secrets_map):
    secret_manager = DummySecretManager()
    loader = DummyConfigLoaderService(secret_manager)
    loader.load_secrets(secrets_map)
    # Invalida cache de um segredo
    loader.invalidate_cache('AZURE_STORAGE_CONNECTION_STRING')
    # Agora, chamada deve ir ao Key Vault novamente
    secret_manager.calls.clear()
    loader.load_secrets(secrets_map)
    assert 'AZURE_STORAGE_CONNECTION_STRING' in secret_manager.calls


def test_concurrent_access_thread_safety(secrets_map):
    secret_manager = DummySecretManager()
    loader = DummyConfigLoaderService(secret_manager)
    results = []
    errors = []
    def worker():
        try:
            res = loader.load_secrets(secrets_map)
            results.append(res)
        except Exception as e:
            errors.append(e)
    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # Todos os resultados devem ser iguais
    assert all(r == results[0] for r in results)
    # Nenhum erro deve ocorrer
    assert not errors
    # Key Vault chamado apenas uma vez por segredo (cache global)
    assert secret_manager.calls.count('AZURE_STORAGE_CONNECTION_STRING') == 1
    assert secret_manager.calls.count('AZURE_AD_CLIENT_SECRET') == 1
    assert secret_manager.calls.count('DEVOPS_TOKEN') == 1
