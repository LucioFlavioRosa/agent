import pytest
from unittest.mock import patch, MagicMock
from backend.app.services.mongodb_service import MongoDBService
from backend.app.services.azure_secret_manager import AzureSecretManager

@pytest.mark.asyncio
async def test_mongodb_service_success():
    with patch.object(AzureSecretManager, 'get_secret') as mock_get_secret:
        mock_get_secret.side_effect = lambda name: {
            'mongodb-uri': 'mongodb://mocked:27017',
            'mongodb-database-name': 'mocked_db'
        }[name]
        service = MongoDBService()
        assert service.mongo_uri == 'mongodb://mocked:27017'
        assert service.db_name == 'mocked_db'
        assert service.client is not None
        assert service.db.name == 'mocked_db'

@pytest.mark.asyncio
async def test_mongodb_service_missing_uri():
    with patch.object(AzureSecretManager, 'get_secret') as mock_get_secret:
        mock_get_secret.side_effect = lambda name: {
            'mongodb-database-name': 'mocked_db'
        }.get(name, None)
        with pytest.raises(EnvironmentError):
            MongoDBService()

@pytest.mark.asyncio
async def test_mongodb_service_missing_db_name():
    with patch.object(AzureSecretManager, 'get_secret') as mock_get_secret:
        mock_get_secret.side_effect = lambda name: {
            'mongodb-uri': 'mongodb://mocked:27017'
        }.get(name, None)
        with pytest.raises(EnvironmentError):
            MongoDBService()

@pytest.mark.asyncio
async def test_mongodb_service_invalid_uri():
    with patch.object(AzureSecretManager, 'get_secret') as mock_get_secret:
        mock_get_secret.side_effect = lambda name: {
            'mongodb-uri': '',
            'mongodb-database-name': 'mocked_db'
        }[name]
        with pytest.raises(EnvironmentError):
            MongoDBService()

@pytest.mark.asyncio
async def test_mongodb_service_invalid_db_name():
    with patch.object(AzureSecretManager, 'get_secret') as mock_get_secret:
        mock_get_secret.side_effect = lambda name: {
            'mongodb-uri': 'mongodb://mocked:27017',
            'mongodb-database-name': ''
        }[name]
        with pytest.raises(EnvironmentError):
            MongoDBService()
