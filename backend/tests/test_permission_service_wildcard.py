import pytest
from unittest.mock import AsyncMock, patch
from backend.app.services.permission_service import PermissionService

@pytest.mark.asyncio
async def test_build_complete_permissions_wildcard():
    """
    Cenário 1: Grupo com allowed_agents ["*"] deve retornar todos os agentes disponíveis.
    """
    # Mock dos agentes disponíveis
    all_agents = ["agent1", "agent2", "agent3"]
    
    # Mock do MCPConfigService
    with patch("backend.app.services.permission_service.MCPConfigService") as mcp_config_mock:
        mcp_config_mock.load_config.return_value.agents = {a: {} for a in all_agents}
        mcp_config_mock.get_agent_config.side_effect = lambda name: {} if name in all_agents else None

        # Mock MongoDBService
        mongo_mock = AsyncMock()
        mongo_mock.get_user_by_email.return_value = AsyncMock(group_ids=["group_wildcard"], active=True, company_id="empresa1")
        mongo_mock.get_group_by_id.return_value = AsyncMock(allowed_agents=["*"])
        
        perm_service = PermissionService(mongo_service=mongo_mock)
        perms = await perm_service._build_complete_permissions("user@teste.com", "empresa1")
        assert set(perms["allowed_agents"]) == set(all_agents)

@pytest.mark.asyncio
async def test_check_user_agent_permission_wildcard():
    """
    Cenário 2: Usuário de grupo com wildcard deve passar na validação para qualquer agente.
    """
    all_agents = ["agent1", "agent2", "agent3"]
    with patch("backend.app.services.permission_service.MCPConfigService") as mcp_config_mock:
        mcp_config_mock.load_config.return_value.agents = {a: {} for a in all_agents}
        mcp_config_mock.get_agent_config.side_effect = lambda name: {} if name in all_agents else None

        mongo_mock = AsyncMock()
        mongo_mock.get_user_by_email.return_value = AsyncMock(group_ids=["group_wildcard"], active=True, company_id="empresa1")
        mongo_mock.get_group_by_id.return_value = AsyncMock(allowed_agents=["*"])
        perm_service = PermissionService(mongo_service=mongo_mock)
        for agent in all_agents:
            allowed, _ = await perm_service.check_user_agent_permission("user@teste.com", agent)
            assert allowed is True

@pytest.mark.asyncio
async def test_check_user_agent_permission_regression():
    """
    Cenário 3: Grupo sem wildcard deve funcionar normalmente (regressão).
    """
    allowed_agents = ["agent1", "agent2"]
    with patch("backend.app.services.permission_service.MCPConfigService") as mcp_config_mock:
        mcp_config_mock.load_config.return_value.agents = {a: {} for a in ["agent1", "agent2", "agent3"]}
        mcp_config_mock.get_agent_config.side_effect = lambda name: {} if name in ["agent1", "agent2", "agent3"] else None

        mongo_mock = AsyncMock()
        mongo_mock.get_user_by_email.return_value = AsyncMock(group_ids=["group_normal"], active=True, company_id="empresa1")
        mongo_mock.get_group_by_id.return_value = AsyncMock(allowed_agents=allowed_agents)
        perm_service = PermissionService(mongo_service=mongo_mock)
        allowed, _ = await perm_service.check_user_agent_permission("user@teste.com", "agent1")
        assert allowed is True
        allowed, _ = await perm_service.check_user_agent_permission("user@teste.com", "agent3")
        assert allowed is False
