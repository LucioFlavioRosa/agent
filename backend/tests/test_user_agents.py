import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from main import app

client = TestClient(app)

@pytest.fixture
def mock_redis_hit():
    with patch("backend.app.services.redis_session_service.RedisSessionService.get_user_permissions") as mock:
        mock.return_value = {
            "allowed_agents": ["agent1", "agent2"],
            "company_id": "empresa123"
        }
        yield mock

@pytest.fixture
def mock_redis_miss():
    with patch("backend.app.services.redis_session_service.RedisSessionService.get_user_permissions") as mock:
        mock.return_value = None
        yield mock

@pytest.fixture
def mock_mongo_user_and_groups():
    with patch("backend.app.services.mongodb_service.MongoDBService.get_user_by_email", new_callable=AsyncMock) as mock_user, \
         patch("backend.app.services.mongodb_service.MongoDBService.get_user_groups", new_callable=AsyncMock) as mock_groups:
        user = type("User", (), {"id": "user123", "email": "user@email.com", "company_id": "empresa123", "group_ids": ["group1", "group2"]})()
        mock_user.return_value = user
        group1 = type("Group", (), {"allowed_agents": ["agent1"]})()
        group2 = type("Group", (), {"allowed_agents": ["agent2", "agent3"]})()
        mock_groups.return_value = [group1, group2]
        yield mock_user, mock_groups

@pytest.mark.asyncio
async def test_agents_success_cache_hit(mock_redis_hit):
    response = client.get("/user/agents?email=user@email.com&empresa=empresa123")
    assert response.status_code == 200
    assert response.json() == {"allowed_agents": ["agent1", "agent2"]}

@pytest.mark.asyncio
async def test_agents_success_cache_miss(mock_redis_miss, mock_mongo_user_and_groups):
    response = client.get("/user/agents?email=user@email.com&empresa=empresa123")
    assert response.status_code == 200
    assert set(response.json()["allowed_agents"]) == {"agent1", "agent2", "agent3"}

@pytest.mark.asyncio
async def test_agents_user_not_found(mock_redis_miss):
    with patch("backend.app.services.mongodb_service.MongoDBService.get_user_by_email", new_callable=AsyncMock) as mock_user:
        mock_user.return_value = None
        response = client.get("/user/agents?email=naoexiste@email.com&empresa=empresa123")
        assert response.status_code == 404
        assert response.json()["detail"] == "Usuário não encontrado."

@pytest.mark.asyncio
async def test_agents_company_id_mismatch(mock_redis_miss):
    with patch("backend.app.services.mongodb_service.MongoDBService.get_user_by_email", new_callable=AsyncMock) as mock_user:
        user = type("User", (), {"id": "user123", "email": "user@email.com", "company_id": "empresaXYZ", "group_ids": ["group1"]})()
        mock_user.return_value = user
        response = client.get("/user/agents?email=user@email.com&empresa=empresa123")
        assert response.status_code == 400
        assert response.json()["detail"] == "Empresa do usuário não corresponde à empresa informada."

@pytest.mark.asyncio
async def test_agents_missing_params():
    response = client.get("/user/agents?email=user@email.com")
    assert response.status_code == 400
    assert response.json()["detail"] == "Parâmetros obrigatórios ausentes: email e empresa."
    response = client.get("/user/agents?empresa=empresa123")
    assert response.status_code == 400
    assert response.json()["detail"] == "Parâmetros obrigatórios ausentes: email e empresa."
