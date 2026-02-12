import pytest
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import io

from backend.app.api.analysis import router as analysis_router

app = FastAPI()
app.include_router(analysis_router, prefix="/analysis")

@pytest.fixture
def client():
 return TestClient(app)

@pytest.mark.asyncio
async def test_analysis_start_accepts_docx(client):
 # Simula um arquivo .docx
 file_content = b"Fake DOCX content"
 file = io.BytesIO(file_content)
 file.name = "test.docx"

 # Mock MCPClientService para garantir que o arquivo é repassado
 with patch("backend.app.services.mcp_client_service.MCPClientService.start_analysis", new_callable=AsyncMock) as mock_start_analysis:
 mock_start_analysis.return_value = type("Resp", (), {"project_id": "mock_project_id", "job_id": "mock_job_id", "nome_projeto": "mock_nome_projeto"})()

 data = {
 "email": "testuser@example.com",
 "nome_projeto": "Projeto Teste",
 "agent_name": "agent1",
 "analysis_type": "code",
 "branch": "main",
 "repository": "https://github.com/test/repo",
 "comentario_extra": "Teste de upload"
 }
 files = {
 "arquivo_docx": ("test.docx", file, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
 }

 response = client.post("/analysis/start", data=data, files=files)

 assert response.status_code == 200
 resp_json = response.json()
 assert "project_id" in resp_json
 assert "job_id" in resp_json
 assert resp_json["project_id"] == "mock_project_id"
 assert resp_json["job_id"] == "mock_job_id"
 # Verifica que o MCPClientService foi chamado com o arquivo
 mock_start_analysis.assert_awaited()
 args, kwargs = mock_start_analysis.call_args
 assert "arquivo_docx" in kwargs or (len(args) > 2 and args[2] is not None)
 # Confirma que o arquivo enviado é de fato .docx
 if "arquivo_docx" in kwargs:
 assert kwargs["arquivo_docx"].filename.endswith(".docx")
 elif len(args) > 2:
 assert args[2].filename.endswith(".docx")

@pytest.mark.asyncio
async def test_analysis_start_rejects_txt_file(client):
 # Simula um arquivo .txt
 file_content = b"Fake TXT content"
 file = io.BytesIO(file_content)
 file.name = "test.txt"

 data = {
 "email": "testuser@example.com",
 "nome_projeto": "Projeto Teste",
 "agent_name": "agent1",
 "analysis_type": "code",
 "branch": "main",
 "repository": "https://github.com/test/repo",
 "comentario_extra": "Teste de upload"
 }
 files = {
 "arquivo_docx": ("test.txt", file, "text/plain")
 }

 # Mock MCPClientService para simular rejeição do arquivo
 with patch("backend.app.services.mcp_client_service.MCPClientService.start_analysis", new_callable=AsyncMock) as mock_start_analysis:
 mock_start_analysis.side_effect = Exception("Arquivo inválido: apenas .docx permitido")

 response = client.post("/analysis/start", data=data, files=files)

 # O backend deve retornar erro apropriado (502 ou 400)
 assert response.status_code in (400, 502)
 resp_json = response.json()
 assert "detail" in resp_json
 assert "docx" in resp_json["detail"] or "inválido" in resp_json["detail"]
