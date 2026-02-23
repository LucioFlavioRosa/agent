import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from main import app

client = TestClient(app)

@pytest.fixture
def mock_blob_upload():
    with patch("main.BlobStorageService.upload_document", new_callable=AsyncMock) as mock_upload:
        mock_upload.return_value = "company_id/cleaned_email/project_id/job_id/documento_recebido.docx"
        yield mock_upload

@pytest.mark.asyncio
async def test_start_analysis_success(mock_blob_upload):
    data = {
        "job_id": "123",
        "project_id": "456",
        "company_id": "789",
        "group_ids": "group1",
        "email": "user.test+foo@example.com",
        "nome_projeto": "Projeto X",
        "analysis_type": "llm",
        "branch": "main",
        "repository": "repo-url",
        "comentario_extra": "Teste"
    }
    files = {
        "arquivo_docx": ("documento_recebido.docx", b"conteudo", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    }

    response = client.post("/api/v1/analysis/start", data=data, files=files)
    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["job_id"] == "123"
    # Verifica se o caminho retornado corresponde ao mock
    assert payload["message"] == "Tarefa adicionada à fila de processamento."
    mock_blob_upload.assert_awaited_once_with(
        company_id="789",
        email="user.test+foo@example.com",
        project_id="456",
        job_id="123",
        filename="documento_recebido.docx",
        file_content=b"conteudo"
    )

@pytest.mark.asyncio
async def test_start_analysis_missing_email(mock_blob_upload):
    data = {
        "job_id": "123",
        "project_id": "456",
        "company_id": "789",
        "group_ids": "group1",
        # email ausente
        "nome_projeto": "Projeto X",
        "analysis_type": "llm",
        "branch": "main",
        "repository": "repo-url",
        "comentario_extra": "Teste"
    }
    files = {
        "arquivo_docx": ("documento_recebido.docx", b"conteudo", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    }

    response = client.post("/api/v1/analysis/start", data=data, files=files)
    assert response.status_code == 400
    assert response.json()["error"] == "O parâmetro 'email' é obrigatório para salvar o documento."
    mock_blob_upload.assert_not_awaited()
