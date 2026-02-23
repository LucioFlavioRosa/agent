import pytest
from unittest.mock import MagicMock, patch

from backend.app.services.vault_service import VaultService, VaultSecretNotFoundError

@pytest.fixture
def vault_service():
    return VaultService()

@patch('backend.app.services.vault_service.SecretClient')
def test_get_secret_with_group_id_success(mock_secret_client, vault_service):
    # Mock retorna segredo para chave com group_id
    mock_instance = mock_secret_client.return_value
    mock_instance.get_secret.return_value = 'supersecret123'
    secret = vault_service.get_secret(
        vault_type='azure',
        key_name='blobstorage-connection-string',
        company_id='acme',
        group_id='dev'
    )
    assert secret == 'supersecret123'
    mock_instance.get_secret.assert_called_with('blobstorage-connection-string-acme-dev')

@patch('backend.app.services.vault_service.SecretClient')
def test_get_secret_fallback_to_company_id(mock_secret_client, vault_service):
    # Mock falha para chave com group_id, sucesso para chave com company_id
    mock_instance = mock_secret_client.return_value
    def side_effect(key):
        if key == 'blobstorage-connection-string-acme-dev':
            raise VaultSecretNotFoundError()
        elif key == 'blobstorage-connection-string-acme':
            return 'fallbacksecret456'
    mock_instance.get_secret.side_effect = side_effect
    secret = vault_service.get_secret(
        vault_type='azure',
        key_name='blobstorage-connection-string',
        company_id='acme',
        group_id='dev'
    )
    assert secret == 'fallbacksecret456'
    mock_instance.get_secret.assert_any_call('blobstorage-connection-string-acme-dev')
    mock_instance.get_secret.assert_any_call('blobstorage-connection-string-acme')

@patch('backend.app.services.vault_service.SecretClient')
def test_get_secret_not_found(mock_secret_client, vault_service):
    # Mock falha para ambos
    mock_instance = mock_secret_client.return_value
    mock_instance.get_secret.side_effect = VaultSecretNotFoundError()
    with pytest.raises(VaultSecretNotFoundError):
        vault_service.get_secret(
            vault_type='azure',
            key_name='blobstorage-connection-string',
            company_id='acme',
            group_id='dev'
        )

@patch('backend.app.services.vault_service.VaultService.get_queue_connection_string')
def test_get_queue_connection_string(mock_get_queue_conn, vault_service):
    mock_get_queue_conn.return_value = 'fixedqueueconnectionstring'
    conn_str = vault_service.get_queue_connection_string()
    assert conn_str == 'fixedqueueconnectionstring'
