import pytest
from unittest.mock import patch, MagicMock
import asyncio
from backend.app.services.mcp_client_service import MCPClientService
from fastapi import UploadFile

@pytest.mark.asyncio
def test_start_analysis_payload_forwarded(monkeypatch):
    # Simula MCPClientService enviando payload simples (sem arquivo)
    mcp_service = MCPClientService(base_url="https://fake-mcp")
    payload = {
        "project_id": "projeto-uuid-123",
        "comentario_extra": "Teste de forwarding",
        "analysis_type": "criacao_epicos_azure_devops",
        "job_id": "job-uuid-456"
    }
    async def mock_post(*args, **kwargs):
        # Verifica que o payload é repassado sem processamento
        assert kwargs.get("json") == payload or kwargs.get("data") == payload
        class Response:
            status_code = 200
            def json(self):
                return {"project_id": payload["project_id"]}
        return Response()
    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    result = asyncio.run(mcp_service.start_analysis(payload))
    assert result.project_id == payload["project_id"]

@pytest.mark.asyncio
def test_start_analysis_with_docx(monkeypatch):
    # Simula envio de arquivo DOCX sem processamento interno
    mcp_service = MCPClientService(base_url="https://fake-mcp")
    payload = {
        "project_id": "projeto-uuid-123",
        "comentario_extra": "Arquivo DOCX",
        "analysis_type": "criacao_epicos_azure_devops",
        "job_id": "job-uuid-456"
    }
    fake_file = MagicMock(spec=UploadFile)
    fake_file.filename = "teste.docx"
    fake_file.content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    fake_file.read = MagicMock(return_value=b"conteudo-docx")
    fake_file.file = MagicMock()
    fake_file.file.seek = MagicMock()
    async def mock_post(*args, **kwargs):
        files = kwargs.get("files")
        assert files is not None
        assert "arquivo_docx" in files
        assert files["arquivo_docx"][0] == "teste.docx"
        assert files["arquivo_docx"][2] == fake_file.content_type
        class Response:
            status_code = 200
            def json(self):
                return {"project_id": payload["project_id"]}
        return Response()
    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    result = asyncio.run(mcp_service.start_analysis(payload, arquivo_docx=fake_file))
    assert result.project_id == payload["project_id"]

@pytest.mark.asyncio
def test_get_projects(monkeypatch):
    # Testa método get_projects do MCPClientService
    mcp_service = MCPClientService(base_url="https://fake-mcp")
    email = "user@example.com"
    empresa = "Peers"
    async def mock_post(*args, **kwargs):
        assert args[1].endswith("/projects/list")
        assert kwargs.get("json") == {"email": email, "empresa": empresa}
        class Response:
            status_code = 200
            def json(self):
                return [
                    {
                        "nome_projeto": "ProjetoNovo",
                        "project_id": "projeto-uuid-123",
                        "ultima_analysis_type": "criacao_epicos_azure_devops",
                        "created_at": "2024-06-01T12:00:00Z",
                        "ultima_atualizacao": "2024-06-01T12:30:00Z"
                    }
                ]
        return Response()
    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    projects = asyncio.run(mcp_service.get_projects(email=email, empresa=empresa))
    assert isinstance(projects, list)
    assert projects[0]["nome_projeto"] == "ProjetoNovo"
    assert projects[0]["project_id"] == "projeto-uuid-123"

@pytest.mark.asyncio
def test_get_report(monkeypatch):
    # Testa método get_report do MCPClientService
    mcp_service = MCPClientService(base_url="https://fake-mcp")
    project_id = "projeto-uuid-123"
    job_id = "job-uuid-456"
    async def mock_post(*args, **kwargs):
        assert args[1].endswith(f"/session/project/{project_id}/{job_id}/reports")
        class Response:
            status_code = 200
            def json(self):
                return {
                    "report_data": {
                        "features_report": [
                            {"id": 101, "nome": "Login"},
                            {"id": 102, "nome": "Cadastro"}
                        ]
                    },
                    "job_id": job_id,
                    "project_id": project_id
                }
        return Response()
    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    report = asyncio.run(mcp_service.get_report(project_id=project_id, job_id=job_id))
    assert "report_data" in report
    assert report["job_id"] == job_id
    assert report["project_id"] == project_id
