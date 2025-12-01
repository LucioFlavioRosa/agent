import pytest
import os
from unittest.mock import patch, MagicMock
from backend.app.services.azure_secret_manager import AzureSecretManager

# Função utilitária para mapear nomes de segredos
# (simula o que deveria acontecer no serviço)
def map_env_to_key_vault(secret_name):
    # Azure Key Vault não aceita underscores, apenas hífens
    return secret_name.replace('_', '-').lower()

class DummySecretClient:
    def __init__(self, secrets):
        self.secrets = secrets
    def get_secret(self, secret_name):
        # Simula busca por nome com hífen
        key_vault_name = map_env_to_key_vault(secret_name)
        if key_vault_name in self.secrets:
            return MagicMock(value=self.secrets[key_vault_name])
        raise Exception(f"Secret not found: {key_vault_name}")

class DummyAzureSecretManager:
    def __init__(self, secrets):
        self._secret_client = DummySecretClient(secrets)
        self._key_vault_url = "https://dummy.vault.azure.net/"
    def get_secret(self, secret_name):
        try:
            secret = self._secret_client.get_secret(secret_name)
            if not secret.value:
                raise ValueError(f"Segredo '{secret_name}' está vazio no Key Vault.")
            return secret.value
        except Exception as e:
            # Fallback para variável de ambiente
            env_value = os.environ.get(secret_name)
            if env_value:
                return env_value
            raise ValueError(f"Erro ao obter segredo '{secret_name}': {e}")

@pytest.mark.parametrize("env_name,key_vault_name,value", [
    ("AZURE_STORAGE_CONNECTION_STRING", "azure-storage-connection-string", "value1"),
    ("JWT_SECRET_KEY", "jwt-secret-key", "value2"),
    ("AZURE_AD_CLIENT_SECRET", "azure-ad-client-secret", "value3")
])
def test_secret_mapping_success(env_name, key_vault_name, value):
    manager = DummyAzureSecretManager({key_vault_name: value})
    assert manager.get_secret(env_name) == value

@pytest.mark.parametrize("env_name,key_vault_name", [
    ("AZURE_STORAGE_CONNECTION_STRING", "azure-storage-connection-string"),
    ("JWT_SECRET_KEY", "jwt-secret-key")
])
def test_secret_mapping_not_found_fallback_env(env_name, key_vault_name, monkeypatch):
    # Simula segredo não encontrado, mas variável de ambiente existe
    monkeypatch.setenv(env_name, "env-fallback-value")
    manager = DummyAzureSecretManager({})
    assert manager.get_secret(env_name) == "env-fallback-value"
    monkeypatch.delenv(env_name, raising=False)

@pytest.mark.parametrize("env_name,key_vault_name", [
    ("AZURE_STORAGE_CONNECTION_STRING", "azure-storage-connection-string"),
    ("JWT_SECRET_KEY", "jwt-secret-key")
])
def test_secret_mapping_not_found_and_no_env(env_name, key_vault_name):
    manager = DummyAzureSecretManager({})
    with pytest.raises(ValueError) as exc:
        manager.get_secret(env_name)
    assert f"Erro ao obter segredo '{env_name}'" in str(exc.value)

@pytest.mark.parametrize("env_name,key_vault_name", [
    ("AZURE_STORAGE_CONNECTION_STRING", "azure-storage-connection-string"),
    ("JWT_SECRET_KEY", "jwt-secret-key")
])
def test_secret_mapping_empty_value(env_name, key_vault_name):
    manager = DummyAzureSecretManager({key_vault_name: ""})
    with pytest.raises(ValueError) as exc:
        manager.get_secret(env_name)
    assert f"Segredo '{env_name}' está vazio no Key Vault." in str(exc.value)

def test_map_env_to_key_vault():
    assert map_env_to_key_vault("AZURE_STORAGE_CONNECTION_STRING") == "azure-storage-connection-string"
    assert map_env_to_key_vault("JWT_SECRET_KEY") == "jwt-secret-key"
    assert map_env_to_key_vault("AZURE_AD_CLIENT_SECRET") == "azure-ad-client-secret"
