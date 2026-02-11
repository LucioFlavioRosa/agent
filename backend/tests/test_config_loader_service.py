import unittest
from unittest.mock import patch, MagicMock
import os
from backend.app.services.config_loader_service import ConfigLoaderService
from backend.app.core.config import settings

class TestConfigLoaderService(unittest.TestCase):
    @patch('backend.app.services.azure_secret_manager.AzureSecretManager')
    def test_success_secret_from_vault(self, mock_secret_manager_cls):
        mock_secret_manager = MagicMock()
        mock_secret_manager.get_secret.return_value = 'vault_value'
        mock_secret_manager_cls.return_value = mock_secret_manager
        service = ConfigLoaderService()
        service._secret_name_to_settings_attr = {'redis-host': 'REDIS_HOST'}
        service._secrets_by_vault = {'azure': ['redis-host']}
        service._vault_map = {'azure': 'kv-url'}
        os.environ['AZURE_KV_URL'] = 'https://fake-vault-url/'
        service.load_secrets_from_key_vault()
        self.assertEqual(getattr(settings, 'REDIS_HOST'), 'vault_value')

    @patch('backend.app.services.azure_secret_manager.AzureSecretManager')
    def test_fallback_to_env(self, mock_secret_manager_cls):
        mock_secret_manager = MagicMock()
        mock_secret_manager.get_secret.side_effect = Exception('404 Not Found')
        mock_secret_manager_cls.return_value = mock_secret_manager
        service = ConfigLoaderService()
        service._secret_name_to_settings_attr = {'redis-host': 'REDIS_HOST'}
        service._secrets_by_vault = {'azure': ['redis-host']}
        service._vault_map = {'azure': 'kv-url'}
        os.environ['REDIS_HOST'] = 'env_value'
        os.environ['AZURE_KV_URL'] = 'https://fake-vault-url/'
        service.load_secrets_from_key_vault()
        self.assertEqual(getattr(settings, 'REDIS_HOST'), 'env_value')

    @patch('backend.app.services.azure_secret_manager.AzureSecretManager')
    def test_missing_required_secret(self, mock_secret_manager_cls):
        mock_secret_manager = MagicMock()
        mock_secret_manager.get_secret.side_effect = Exception('404 Not Found')
        mock_secret_manager_cls.return_value = mock_secret_manager
        service = ConfigLoaderService()
        service._secret_name_to_settings_attr = {'redis-host': 'REDIS_HOST'}
        service._secrets_by_vault = {'azure': ['redis-host']}
        service._vault_map = {'azure': 'kv-url'}
        if 'REDIS_HOST' in os.environ:
            del os.environ['REDIS_HOST']
        os.environ['AZURE_KV_URL'] = 'https://fake-vault-url/'
        service.load_secrets_from_key_vault()
        self.assertIsNone(getattr(settings, 'REDIS_HOST', None))

if __name__ == '__main__':
    unittest.main()
