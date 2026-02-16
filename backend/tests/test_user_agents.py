import pytest
import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def app():
    from backend.app.api.user_agents import router as user_agents_router
    test_app = FastAPI()
    test_app.include_router(user_agents_router, prefix="/user")
    return test_app

@pytest.fixture
def client(app):
    return TestClient(app)

@pytest.mark.asyncio
async def test_get_user_agents_success_from_cache(mocker, app):
    # Mock RedisSessionService
    mock_redis = MagicMock()
    mock_redis.get_user_permissions.return_value = {
        "allowed_agents": ["agent1", "agent2"]
    }
    mocker.patch("backend.app.services.redis_session_service.RedisSessionService", return_value=mock_redis)
    # Mock MongoDBService não será chamado
    response = await app.router.routes[0].endpoint(
        email="user@example.com",
        empresa="company123",
        mongo_service=MagicMock()
    )
    assert response == {"allowed_agents": ["agent1", "agent2"]}

@pytest.mark.asyncio
async def test_get_user_agents_success_from_mongo(mocker, app):
    # Redis retorna None (cache miss)
    mock_redis = MagicMock()
    mock_redis.get_user_permissions.return_value = None
    mocker.patch("backend.app.services.redis_session_service.RedisSessionService", return_value=mock_redis)
    # Mongo retorna usuário com grupos
    mock_mongo = MagicMock()
    user = MagicMock()
    user.group_ids = ["group1", "group2"]
    user.company_id = "company123"
    mock_mongo.get_user_by_email = AsyncMock(return_value=user)
    mock_mongo.get_group_allowed_agents = AsyncMock(side_effect=[["agent1"], ["agent2", "agent3"]])
    response = await app.router.routes[0].endpoint(
        email="user@example.com",
        empresa="company123",
        mongo_service=mock_mongo
    )
    assert set(response["allowed_agents"]) == {"agent1", "agent2", "agent3"}

@pytest.mark.asyncio
async def test_get_user_agents_user_not_found(mocker, app):
    mock_redis = MagicMock()
    mock_redis.get_user_permissions.return_value = None
    mocker.patch("backend.app.services.redis_session_service.RedisSessionService", return_value=mock_redis)
    mock_mongo = MagicMock()
    mock_mongo.get_user_by_email = AsyncMock(return_value=None)
    with pytest.raises(Exception) as exc:
        await app.router.routes[0].endpoint(
            email="notfound@example.com",
            empresa="company123",
            mongo_service=mock_mongo
        )
    assert "Usuário não encontrado" in str(exc.value)

@pytest.mark.asyncio
async def test_get_user_agents_company_mismatch(mocker, app):
    mock_redis = MagicMock()
    mock_redis.get_user_permissions.return_value = None
    mocker.patch("backend.app.services.redis_session_service.RedisSessionService", return_value=mock_redis)
    mock_mongo = MagicMock()
    user = MagicMock()
    user.group_ids = ["group1"]
    user.company_id = "company999"
    mock_mongo.get_user_by_email = AsyncMock(return_value=user)
    with pytest.raises(Exception) as exc:
        await app.router.routes[0].endpoint(
            email="user@example.com",
            empresa="company123",
            mongo_service=mock_mongo
        )
    assert "Você não tem permissão para acessar os dados desta empresa" in str(exc.value)

@pytest.mark.asyncio
async def test_get_user_agents_no_groups(mocker, app):
    mock_redis = MagicMock()
    mock_redis.get_user_permissions.return_value = None
    mocker.patch("backend.app.services.redis_session_service.RedisSessionService", return_value=mock_redis)
    mock_mongo = MagicMock()
    user = MagicMock()
    user.group_ids = []
    user.company_id = "company123"
    mock_mongo.get_user_by_email = AsyncMock(return_value=user)
    response = await app.router.routes[0].endpoint(
        email="user@example.com",
        empresa="company123",
        mongo_service=mock_mongo
    )
    assert response["allowed_agents"] == []
