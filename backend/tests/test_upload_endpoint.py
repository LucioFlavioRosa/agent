import io
import pytest
from fastapi import FastAPI, UploadFile, Form, BackgroundTasks, Depends, HTTPException, status
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from backend.app.main import app

@pytest.fixture
def client():
    return TestClient(app)

class DummyUser:
    def __init__(self, usuario_executor="user@example.com", sub="user_sub"):
        self.usuario_executor = usuario_executor
        self.sub = sub

# Helper para criar arquivo docx válido em memória
from docx import Document

def create_docx_bytes(text="Texto de teste"):
    doc = Document()
    doc.add_paragraph(text)
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    return file_stream.read()

def test_upload_docx_success(client):
    # Mock dependências externas: upload_docx_to_blob, extract_text_from_docx, MCPClientService
    with patch("backend.app.services.blob_storage_service.upload_docx_to_blob", return_value="https://fake.blob.url/file.docx"), \
         patch("backend.app.services.docx_parser_service.extract_text_from_docx", return_value="Texto extraido"), \
         patch("backend.app.services.mcp_client_service.MCPClientService.start_analysis", return_value=MagicMock(job_id="job-123")):
        token = "valid-token"
        docx_bytes = create_docx_bytes()
        response = client.post(
            "/upload/docx",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("teste.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={
                "projeto": "ProjetoX",
                "analysis_name": "Analise01",
                "analysis_type": "criacao_epicos_azure_devops"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job-123"
        assert data["blob_url"] == "https://fake.blob.url/file.docx"
        assert "sucesso" in data["message"]

def test_upload_docx_invalid_token(client):
    # Token inválido
    docx_bytes = create_docx_bytes()
    response = client.post(
        "/upload/docx",
        headers={"Authorization": "Bearer invalid-token"},
        files={"file": ("teste.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={
            "projeto": "ProjetoX",
            "analysis_name": "Analise01",
            "analysis_type": "criacao_epicos_azure_devops"
        }
    )
    assert response.status_code == 401
    assert "Token Azure AD inválido" in response.json()["detail"] or "Token JWT inválido ou ausente" in response.json()["detail"]

def test_upload_docx_expired_token(client):
    # Token expirado
    docx_bytes = create_docx_bytes()
    response = client.post(
        "/upload/docx",
        headers={"Authorization": "Bearer expired-token"},
        files={"file": ("teste.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={
            "projeto": "ProjetoX",
            "analysis_name": "Analise01",
            "analysis_type": "criacao_epicos_azure_devops"
        }
    )
    assert response.status_code == 401
    assert "Token Azure AD expirado" in response.json()["detail"] or "Token JWT inválido ou ausente" in response.json()["detail"]

def test_upload_docx_invalid_file_extension(client):
    # Arquivo não .docx
    response = client.post(
        "/upload/docx",
        headers={"Authorization": "Bearer valid-token"},
        files={"file": ("teste.txt", b"texto qualquer", "text/plain")},
        data={
            "projeto": "ProjetoX",
            "analysis_name": "Analise01",
            "analysis_type": "criacao_epicos_azure_devops"
        }
    )
    assert response.status_code == 400
    assert "Apenas arquivos .docx" in response.json()["detail"]

def test_upload_docx_docx_extraction_error(client):
    # Erro ao extrair texto do docx
    with patch("backend.app.services.docx_parser_service.extract_text_from_docx", side_effect=Exception("Falha na extração")):
        docx_bytes = create_docx_bytes()
        response = client.post(
            "/upload/docx",
            headers={"Authorization": "Bearer valid-token"},
            files={"file": ("teste.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={
                "projeto": "ProjetoX",
                "analysis_name": "Analise01",
                "analysis_type": "criacao_epicos_azure_devops"
            }
        )
        assert response.status_code == 400
        assert "Erro ao extrair texto do docx" in response.json()["detail"]

def test_upload_docx_mcp_server_error(client):
    # Erro ao comunicar com MCP Server
    with patch("backend.app.services.blob_storage_service.upload_docx_to_blob", return_value="https://fake.blob.url/file.docx"), \
         patch("backend.app.services.docx_parser_service.extract_text_from_docx", return_value="Texto extraido"), \
         patch("backend.app.services.mcp_client_service.MCPClientService.start_analysis", side_effect=Exception("Falha MCP Server")):
        docx_bytes = create_docx_bytes()
        response = client.post(
            "/upload/docx",
            headers={"Authorization": "Bearer valid-token"},
            files={"file": ("teste.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={
                "projeto": "ProjetoX",
                "analysis_name": "Analise01",
                "analysis_type": "criacao_epicos_azure_devops"
            }
        )
        assert response.status_code == 502
        assert "Erro ao comunicar com MCP Server" in response.json()["detail"]
