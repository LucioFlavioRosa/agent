import pytest
import logging
from backend.app.services.mcp_client_service import MCPClientService

@pytest.mark.asyncio
def test_start_analysis_logs(monkeypatch, caplog):
    caplog.set_level("INFO")
    # Mock httpx.AsyncClient
    class DummyResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return {"project_id": "pid", "job_id": "jid"}
    class DummyAsyncClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
        async def post(self, url, data=None, files=None, json=None):
            logging.getLogger("mcp_client_service").info(f"POST enviado para {url}")
            return DummyResponse()
    monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: DummyAsyncClient())

    payload = {
        "project_id": "pid",
        "job_id": "jid",
        "email": "user@peers.com",
        "nome_projeto": "Projeto Teste",
        "agent_name": "agente_dummy",
        "analysis_type": "static",
        "branch": "main",
        "repository": "repo-url",
        "comentario_extra": "Teste de log"
    }
    mcp_service_url = "http://dummy-mcp"
    service = MCPClientService(base_url=mcp_service_url)

    # Chama método e valida logs
    import asyncio
    asyncio.run(service.start_analysis(payload, mcp_service_url))
    logs = caplog.text
    assert f"POST enviado para {mcp_service_url}/start" in logs
