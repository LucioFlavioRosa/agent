import pytest
import uuid
from unittest.mock import patch, AsyncMock
from backend.app.services.mcp_client_service import MCPClientService
from fastapi import UploadFile

@pytest.mark.asyncio
async def test_start_analysis_includes_job_id_in_payload():
    # Setup
    mcp_service_url = 'http://fake-mcp-service'
    job_id = str(uuid.uuid4())
    payload = {
        "project_id": "proj123",
        "job_id": job_id,
        "email": "user@example.com",
        "nome_projeto": "Projeto Teste",
        "agent_name": "agentA",
        "analysis_type": "agentA",
        "branch": "main",
        "repository": "repo-url",
        "comentario_extra": "comentário"
    }

    # Mock response do MCP
    mcp_response = {
        "project_id": payload["project_id"],
        "job_id": payload["job_id"]
    }

    async def mock_post(*args, **kwargs):
        # Verifica que o job_id está no payload enviado
        if 'data' in kwargs:
            sent = kwargs['data']
        elif 'json' in kwargs:
            sent = kwargs['json']
        else:
            sent = {}
        assert sent.get('job_id') == job_id
        return AsyncMock(status_code=200, json=lambda: mcp_response)()

    with patch('httpx.AsyncClient.post', new=mock_post):
        client = MCPClientService(base_url=mcp_service_url)
        result = await client.start_analysis(payload, mcp_service_url)
        assert result.project_id == payload["project_id"]
        assert result.job_id == job_id
        # Verifica que o job_id é um UUID válido
        assert uuid.UUID(result.job_id)
