import pytest
from unittest.mock import MagicMock
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.services.mongodb_service import MongoDBService

@pytest.fixture
def mock_redis(mocker):
    mock_client = MagicMock()
    mocker.patch('backend.app.services.redis_session_service.redis.Redis', return_value=mock_client)
    return mock_client

@pytest.fixture
def redis_service(mock_redis):
    return RedisSessionService()

@pytest.fixture
def mock_mongo(mocker):
    mock_service = MagicMock(spec=MongoDBService)
    return mock_service

@pytest.fixture
def email():
    return "user@example.com"

@pytest.fixture
def company_id():
    return "company123"

@pytest.fixture
def permissions():
    return {"can_create_projects": True, "allowed_agents": ["agent1", "agent2"]}

@pytest.mark.asyncio
async def test_cache_miss(redis_service, mock_redis, mock_mongo, email, company_id, permissions):
    # Simula cache miss: Redis não tem a chave, Mongo retorna permissões
    mock_redis.get.return_value = None
    mock_mongo.get_user_by_email.return_value = MagicMock(company_id=company_id)
    mock_mongo.get_user_groups.return_value = [MagicMock(company_id=company_id, settings=permissions)]
    # Simula lógica de buscar permissões e salvar no Redis
    # (exemplo: PermissionService().check_user_can_create_project)
    redis_service.store_user_permissions(email, company_id, permissions)
    mock_redis.setex.assert_called()

@pytest.mark.asyncio
async def test_cache_hit(redis_service, mock_redis, email, company_id, permissions):
    # Simula cache hit: Redis já tem a chave
    mock_redis.get.return_value = '{"can_create_projects": true, "allowed_agents": ["agent1", "agent2"]}'
    perms = redis_service.get_user_permissions(email, company_id)
    assert perms["can_create_projects"] is True
    assert "agent1" in perms["allowed_agents"]
    mock_redis.get.assert_called()

@pytest.mark.asyncio
async def test_cache_invalidation(redis_service, mock_redis, email, company_id):
    # Simula remoção do cache
    redis_service.invalidate_user_permissions(email, company_id)
    mock_redis.delete.assert_called_with(f"perms:{email}:{company_id}")

@pytest.mark.asyncio
async def test_cache_expiration(redis_service, mock_redis, mock_mongo, email, company_id, permissions):
    # Simula expiração do cache: Redis não tem a chave, Mongo é chamado novamente
    mock_redis.get.return_value = None
    mock_mongo.get_user_by_email.return_value = MagicMock(company_id=company_id)
    mock_mongo.get_user_groups.return_value = [MagicMock(company_id=company_id, settings=permissions)]
    redis_service.store_user_permissions(email, company_id, permissions)
    mock_redis.setex.assert_called()
