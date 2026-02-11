import unittest
from unittest.mock import patch, MagicMock
from backend.app.services.azure_secret_manager import AzureSecretManager

class TestAzureSecretManager(unittest.TestCase):
    @patch('azure.keyvault.secrets.SecretClient')
    @patch('azure.identity.DefaultAzureCredential')
    def test_get_secret_success(self, mock_credential_cls, mock_secret_client_cls):
        mock_secret_client = MagicMock()
        mock_secret = MagicMock()
        mock_secret.value = 'my_secret_value'
        mock_secret_client.get_secret.return_value = mock_secret
        mock_secret_client_cls.return_value = mock_secret_client
        os.environ['AZURE_KV_URL'] = 'https://fake-vault-url/'
        manager = AzureSecretManager(vault_type='azure')
        value = manager.get_secret('test-secret')
        self.assertEqual(value, 'my_secret_value')

    @patch('azure.keyvault.secrets.SecretClient')
    @patch('azure.identity.DefaultAzureCredential')
    def test_get_secret_not_found(self, mock_credential_cls, mock_secret_client_cls):
        mock_secret_client = MagicMock()
        mock_secret_client.get_secret.side_effect = Exception('404 Not Found')
        mock_secret_client_cls.return_value = mock_secret_client
        os.environ['AZURE_KV_URL'] = 'https://fake-vault-url/'
        manager = AzureSecretManager(vault_type='azure')
        with self.assertRaises(ValueError):
            manager.get_secret('missing-secret')

    def test_invalid_vault_url(self):
        if 'AZURE_KV_URL' in os.environ:
            del os.environ['AZURE_KV_URL']
        with self.assertRaises(EnvironmentError):
            AzureSecretManager(vault_type='azure')

if __name__ == '__main__':
    unittest.main()
