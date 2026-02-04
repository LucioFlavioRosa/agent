import pytest
from unittest.mock import MagicMock, patch

# Supondo que a função get_blob_container_name está em tools.blob_storage_utils
from tools.blob_storage_utils import get_blob_container_name

class DummyGroupResolver:
    def get_group_for_user(self, user_email):
        return "grupo"

class DummySecretManager:
    def get_secret(self, secret_name):
        if secret_name == "azure-storage-container-name-grupo-peers":
            return "container-grupo-peers"
        raise KeyError(f"Secret {secret_name} not found")

class DummyUserEmailParser:
    @staticmethod
    def parse_email(user_email):
        return ("usuario", "peers")

@patch("tools.blob_storage_utils.UserEmailParser", DummyUserEmailParser)
def test_get_blob_container_name_success():
    group_resolver = DummyGroupResolver()
    secret_manager = DummySecretManager()
    user_email = "usuario@peers.com"
    container_name = get_blob_container_name(secret_manager, user_email, group_resolver)
    assert container_name == "container-grupo-peers"

@patch("tools.blob_storage_utils.UserEmailParser", DummyUserEmailParser)
def test_get_blob_container_name_secret_not_found():
    group_resolver = DummyGroupResolver()
    class FailingSecretManager:
        def get_secret(self, secret_name):
            raise KeyError(f"Secret {secret_name} not found")
    secret_manager = FailingSecretManager()
    user_email = "usuario@peers.com"
    with pytest.raises(KeyError) as excinfo:
        get_blob_container_name(secret_manager, user_email, group_resolver)
    assert "not found" in str(excinfo.value)
