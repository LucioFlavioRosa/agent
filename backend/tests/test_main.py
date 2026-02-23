import pytest
import asyncio
from httpx import AsyncClient
from fastapi import status
from backend.app.services.blob_storage_service import BlobStorageConnectionError, BlobUploadError

@pytest.fixture
def mock_blob_service(mocker):
    return mocker.patch('main.BlobStorageService')

@pytest.fixture
def mock_vault_service(mocker):
    return mocker.patch('main.vault_service')

@pytest.mark.asyncio
async def test_start_analysis_with_file_upload_success(mocker):
    mock_upload = mocker.patch('main.BlobStorageService.upload_document', new_callable=asyncio.coroutine)
    mock_upload.return_value = 'comp123/proj456/job789/documento_recebido.docx'
    async with AsyncClient(app=app, base_url="http://test") as ac:
        file_content = b'dummy'
        response = await ac.post("/api/v1/analysis/start", files={"arquivo_docx": ("documento_recebido.docx", file_content)}, data={"job_id": "job789", "project_id": "proj456", "company_id": "comp123"})
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["status"] == "queued"
        assert "job_id" in data
        assert "message" in data

@pytest.mark.asyncio
async def test_start_analysis_blob_connection_error(mocker):
    mock_upload = mocker.patch('main.BlobStorageService.upload_document', side_effect=BlobStorageConnectionError)
    async with AsyncClient(app=app, base_url="http://test") as ac:
        file_content = b'dummy'
        response = await ac.post("/api/v1/analysis/start", files={"arquivo_docx": ("documento_recebido.docx", file_content)}, data={"job_id": "job789", "project_id": "proj456", "company_id": "comp123"})
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "error" in response.json()

@pytest.mark.asyncio
async def test_start_analysis_blob_upload_error(mocker):
    mock_upload = mocker.patch('main.BlobStorageService.upload_document', side_effect=BlobUploadError)
    async with AsyncClient(app=app, base_url="http://test") as ac:
        file_content = b'dummy'
        response = await ac.post("/api/v1/analysis/start", files={"arquivo_docx": ("documento_recebido.docx", file_content)}, data={"job_id": "job789", "project_id": "proj456", "company_id": "comp123"})
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "error" in response.json()
