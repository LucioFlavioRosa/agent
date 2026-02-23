import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_start_analysis_with_file(client):
    # Mock upload_document
    with patch("main.BlobService.upload_document", new_callable=AsyncMock) as mock_upload_document:
        mock_upload_document.return_value = "company_id/email/project_id/job_id/documento_recebido.docx"
        data = {
            "job_id": "123",
            "project_id": "proj1",
            "company_id": "company_id",
            "group_ids": "group1",
            "email": "user@example.com",
            "nome_projeto": "Projeto Teste",
            "analysis_type": "typeA",
            "branch": "main",
            "repository": "repo",
            "comentario_extra": "comentario"
        }
        file_content = b"dummy content"
        files = {"arquivo_docx": ("documento_recebido.docx", file_content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        response = client.post("/api/v1/analysis/start", data=data, files=files)
        assert response.status_code == 202
        payload = response.json()
        assert payload["status"] == "queued"
        assert payload["job_id"] == "123"
        # Verifica se o mock foi chamado com os parâmetros corretos
        mock_upload_document.assert_awaited_once_with(
            company_id="company_id",
            email="user@example.com",
            project_id="proj1",
            job_id="123",
            filename="documento_recebido.docx",
            file_content=file_content
        )
        # Verifica se o caminho está correto no payload
        assert payload["message"] == "Tarefa adicionada à fila de processamento."

@pytest.mark.asyncio
async def test_start_analysis_file_without_email(client):
    # Mock upload_document
    with patch("main.BlobService.upload_document", new_callable=AsyncMock) as mock_upload_document:
        mock_upload_document.return_value = "company_id/_/proj1/123/documento_recebido.docx"
        data = {
            "job_id": "123",
            "project_id": "proj1",
            "company_id": "company_id",
            "group_ids": "group1",
            "nome_projeto": "Projeto Teste",
            "analysis_type": "typeA",
            "branch": "main",
            "repository": "repo",
            "comentario_extra": "comentario"
        }
        file_content = b"dummy content"
        files = {"arquivo_docx": ("documento_recebido.docx", file_content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        response = client.post("/api/v1/analysis/start", data=data, files=files)
        assert response.status_code == 500
        payload = response.json()
        assert "error" in payload
        assert payload["error"] == "Falha de credenciais do Blob Storage."
