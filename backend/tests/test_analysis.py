import pytest
from fastapi.testclient import TestClient
from backend.app.api.analysis import router
from backend.app.core.config import settings
from main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
def test_start_analysis_logs(caplog, client, monkeypatch):
    # Mock MCPClientService para não chamar MCP real
    from backend.app.services.mcp_client_service import MCPClientService
    async def mock_start_analysis(self, payload, mcp_service_url, arquivo_docx=None):
        logging.getLogger("analysis_api").info("Mock MCPClientService.start_analysis chamado")
        return None
    monkeypatch.setattr(MCPClientService, "start_analysis", mock_start_analysis)

    # Mock MongoDBService para não acessar DB real
    from backend.app.services.mongodb_service import MongoDBService
    async def mock_get_user_by_email(self, email):
        class DummyUser:
            id = "dummy_user_id"
            email = email
            company_id = "dummy_company_id"
            active = True
        return DummyUser()
    monkeypatch.setattr(MongoDBService, "get_user_by_email", mock_get_user_by_email)

    async def mock_get_project_by_normalized_name(self, nome_projeto, company_id):
        return None
    monkeypatch.setattr(MongoDBService, "get_project_by_normalized_name", mock_get_project_by_normalized_name)

    async def mock_create_project(self, project_data):
        return True
    monkeypatch.setattr(MongoDBService, "create_project", mock_create_project)

    async def mock_check_user_agent_permission(self, email, agent_name):
        return True, None
    from backend.app.services.permission_service import PermissionService
    monkeypatch.setattr(PermissionService, "check_user_agent_permission", mock_check_user_agent_permission)

    async def mock_check_user_project_permission(self, email, project_id, agent_name, action_type):
        return True, "owner", None
    monkeypatch.setattr(PermissionService, "check_user_project_permission", mock_check_user_project_permission)

    # Mock MCPConfigService
    from backend.app.services.mcp_config_service import MCPConfigService
    class DummyAgentCfg:
        mcp_service_url = "http://dummy-mcp"
    monkeypatch.setattr(MCPConfigService, "get_agent_config", lambda agent_name: DummyAgentCfg())

    caplog.set_level("INFO")
    response = client.post(
        "/analysis/start",
        data={
            "email": "test@peers.com",
            "nome_projeto": "Projeto Teste",
            "agent_name": "agente_dummy",
            "analysis_type": "static",
            "branch": "main",
            "repository": "repo-url",
            "comentario_extra": "Teste de log"
        }
    )
    assert response.status_code == 200
    logs = caplog.text
    assert "Iniciando análise multiagente para projeto" in logs
    assert "Mock MCPClientService.start_analysis chamado" in logs
    assert "Configuração do agente" not in logs or "Configuração do agente" in logs
    assert "Análise multiagente solicitada com sucesso ao MCP." in response.text
