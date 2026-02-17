import pytest
from unittest.mock import AsyncMock, patch
from backend.app.services.permission_service import PermissionService
from backend.app.services.redis_session_service import RedisSessionService

@pytest.mark.asyncio
async def test_integration_wildcard_group_cache_and_invalidation():
    """
    Teste de integração: Cria grupo com wildcard, associa usuário, valida cache Redis e invalida após modificação.
    """
    all_agents = ["agent1", "agent2", "agent3"]
    with patch("backend.app.services.permission_service.MCPConfigService") as mcp_config_mock:
        mcp_config_mock.load_config.return_value.agents = {a: {} for a in all_agents}
        mcp_config_mock.get_agent_config.side_effect = lambda name: {} if name in all_agents else None

        # Mock MongoDBService
        mongo_mock = AsyncMock()
        mongo_mock.get_user_by_email.return_value = AsyncMock(group_ids=["group_wildcard"], active=True, company_id="empresa1")
        mongo_mock.get_group_by_id.return_value = AsyncMock(allowed_agents=["*"])

        # Mock RedisSessionService
        redis_mock = AsyncMock()
        redis_mock.get_user_permissions.return_value = None
        redis_mock.store_user_permissions = AsyncMock()
        redis_mock.invalidate_user_permissions = AsyncMock()

        perm_service = PermissionService(mongo_service=mongo_mock, redis_session_service=redis_mock)
        perms = await perm_service._build_complete_permissions("user@teste.com", "empresa1")
        assert set(perms["allowed_agents"]) == set(all_agents)
        redis_mock.store_user_permissions.assert_called_with("user@teste.com", "empresa1", perms)

        # Simula modificação no grupo e invalidação
        await redis_mock.invalidate_user_permissions("user@teste.com", "empresa1")
        redis_mock.invalidate_user_permissions.assert_called_with("user@teste.com", "empresa1")
