import pytest
from unittest.mock import AsyncMock, patch

class SecretNotFoundException(Exception):
    pass

class FakeSecretClient:
    def __init__(self, secrets):
        self.secrets = secrets
        self.called = []
    async def get_secret(self, name):
        self.called.append(name)
        if name in self.secrets:
            class Value:
                value = self.secrets[name]
            return Value()
        raise Exception("Secret not found")

class SecretsManager:
    def __init__(self, client):
        self.client = client
        self.cache = {}
    async def get_secret(self, base_name, company_id, group_id=None):
        patterns = []
        if group_id:
            patterns.append(f"{base_name}-{company_id}-{group_id}")
        patterns.append(f"{base_name}-{company_id}")
        for name in patterns:
            if name in self.cache:
                return self.cache[name]
            try:
                secret = await self.client.get_secret(name)
                self.cache[name] = secret.value
                return secret.value
            except Exception:
                continue
        raise SecretNotFoundException(f"Secret not found for: {base_name}, company: {company_id}, group: {group_id}")

@pytest.mark.asyncio
async def test_get_secret_success_with_group():
    secrets = {
        "blobstorage-conection-string-123-456": "conn_group",
        "blobstorage-conection-string-123": "conn_company"
    }
    client = FakeSecretClient(secrets)
    manager = SecretsManager(client)
    result = await manager.get_secret("blobstorage-conection-string", "123", "456")
    assert result == "conn_group"
    assert "blobstorage-conection-string-123-456" in client.called

@pytest.mark.asyncio
async def test_get_secret_fallback_to_company():
    secrets = {
        "blobstorage-conection-string-123": "conn_company"
    }
    client = FakeSecretClient(secrets)
    manager = SecretsManager(client)
    result = await manager.get_secret("blobstorage-conection-string", "123", "456")
    assert result == "conn_company"
    assert "blobstorage-conection-string-123-456" in client.called
    assert "blobstorage-conection-string-123" in client.called

@pytest.mark.asyncio
async def test_get_secret_not_found():
    secrets = {}
    client = FakeSecretClient(secrets)
    manager = SecretsManager(client)
    with pytest.raises(SecretNotFoundException):
        await manager.get_secret("blobstorage-conection-string", "123", "456")

@pytest.mark.asyncio
async def test_cache_functionality():
    secrets = {
        "blobstorage-conection-string-123": "conn_company"
    }
    client = FakeSecretClient(secrets)
    manager = SecretsManager(client)
    result1 = await manager.get_secret("blobstorage-conection-string", "123")
    result2 = await manager.get_secret("blobstorage-conection-string", "123")
    assert result1 == result2 == "conn_company"
    # Only one call to client.get_secret for the same secret
    assert client.called.count("blobstorage-conection-string-123") == 1
