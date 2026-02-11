import pytest
from unittest.mock import patch, MagicMock
from backend.app.services.startup_validator import StartupValidator

@pytest.fixture
def validator():
    return StartupValidator()

@pytest.mark.asyncio
async def test_validate_mongodb_connection_success(validator):
    with patch('backend.app.core.config.settings') as mock_settings, \
         patch('motor.motor_asyncio.AsyncIOMotorClient') as mock_client:
        mock_settings.MONGODB_URI = 'mongodb://mocked:27017'
        mock_settings.MONGODB_DATABASE_NAME = 'mocked_db'
        mock_db = MagicMock()
        mock_db.command.return_value = {'ok': 1.0}
        mock_client.return_value.__getitem__.return_value = mock_db
        validator.validate_mongodb_connection()
        assert validator.status_report['mongodb']['status'] == 'ok'
        assert 'Conexão com MongoDB bem-sucedida.' in validator.status_report['mongodb']['detail']

@pytest.mark.asyncio
async def test_validate_mongodb_connection_fail_missing_settings(validator):
    with patch('backend.app.core.config.settings') as mock_settings:
        mock_settings.MONGODB_URI = None
        mock_settings.MONGODB_DATABASE_NAME = None
        validator.validate_mongodb_connection()
        assert validator.status_report['mongodb']['status'] == 'fail'
        assert 'não configurados' in validator.status_report['mongodb']['detail']

@pytest.mark.asyncio
async def test_validate_mongodb_connection_fail_ping(validator):
    with patch('backend.app.core.config.settings') as mock_settings, \
         patch('motor.motor_asyncio.AsyncIOMotorClient') as mock_client:
        mock_settings.MONGODB_URI = 'mongodb://mocked:27017'
        mock_settings.MONGODB_DATABASE_NAME = 'mocked_db'
        mock_db = MagicMock()
        mock_db.command.return_value = {'ok': 0.0}
        mock_client.return_value.__getitem__.return_value = mock_db
        validator.validate_mongodb_connection()
        assert validator.status_report['mongodb']['status'] == 'fail'
        assert 'Falha ao conectar ao MongoDB.' in validator.status_report['mongodb']['detail']

@pytest.mark.asyncio
async def test_validate_mongodb_connection_exception(validator):
    with patch('backend.app.core.config.settings') as mock_settings, \
         patch('motor.motor_asyncio.AsyncIOMotorClient') as mock_client:
        mock_settings.MONGODB_URI = 'mongodb://mocked:27017'
        mock_settings.MONGODB_DATABASE_NAME = 'mocked_db'
        mock_client.side_effect = Exception('mocked exception')
        validator.validate_mongodb_connection()
        assert validator.status_report['mongodb']['status'] == 'fail'
        assert 'Erro ao conectar ao MongoDB' in validator.status_report['mongodb']['detail']

@pytest.mark.asyncio
async def test_validate_redis_connection_success(validator):
    with patch('backend.app.core.config.settings') as mock_settings, \
         patch('redis.Redis') as mock_redis:
        mock_settings.REDIS_HOST = 'mocked_host'
        mock_settings.REDIS_PORT = 6379
        mock_settings.REDIS_PASSWORD = 'mocked_pass'
        mock_settings.REDIS_DB = 0
        mock_settings.REDIS_USE_SSL = False
        mock_settings.REDIS_SSL_CERT_REQS = None
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis.return_value = mock_client
        validator.validate_redis_connection()
        assert validator.status_report['redis']['status'] == 'ok'
        assert 'Conexão com Redis via endpoint privado e SSL bem-sucedida.' in validator.status_report['redis']['detail']

@pytest.mark.asyncio
async def test_validate_redis_connection_fail_missing_secrets(validator):
    with patch('backend.app.core.config.settings') as mock_settings:
        mock_settings.REDIS_HOST = None
        mock_settings.REDIS_PORT = None
        mock_settings.REDIS_PASSWORD = None
        mock_settings.REDIS_DB = None
        mock_settings.REDIS_USE_SSL = None
        mock_settings.REDIS_SSL_CERT_REQS = None
        validator.validate_redis_connection()
        assert validator.status_report['redis']['status'] == 'fail'
        assert 'Segredos do Redis não carregados' in validator.status_report['redis']['detail']

@pytest.mark.asyncio
async def test_validate_redis_connection_exception(validator):
    with patch('backend.app.core.config.settings') as mock_settings, \
         patch('redis.Redis') as mock_redis:
        mock_settings.REDIS_HOST = 'mocked_host'
        mock_settings.REDIS_PORT = 6379
        mock_settings.REDIS_PASSWORD = 'mocked_pass'
        mock_settings.REDIS_DB = 0
        mock_settings.REDIS_USE_SSL = False
        mock_settings.REDIS_SSL_CERT_REQS = None
        mock_redis.side_effect = Exception('mocked redis exception')
        validator.validate_redis_connection()
        assert validator.status_report['redis']['status'] == 'fail'
        assert 'Erro ao conectar ao Redis' in validator.status_report['redis']['detail']

@pytest.mark.asyncio
async def test_validate_all_configs_success(validator):
    with patch.object(validator, 'validate_mongodb_connection') as mock_mongo, \
         patch.object(validator, 'validate_redis_connection') as mock_redis:
        mock_mongo.return_value = None
        mock_redis.return_value = None
        validator.status_report = {'mongodb': {'status': 'ok'}, 'redis': {'status': 'ok'}}
        status = validator.validate_all_configs()
        assert status['mongodb']['status'] == 'ok'
        assert status['redis']['status'] == 'ok'
