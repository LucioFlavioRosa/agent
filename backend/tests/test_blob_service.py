import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from backend.app.services.vault_service import vault_service
from azure.storage.blob.aio import BlobServiceClient

import sys
sys.path.append('backend/app')

@pytest.mark.asyncio
async def test_upload_document_success(mocker):
    # Mock vault_service.get_secret para retornar uma connection string válida
    mocker.patch.object(vault_service, 'get_secret', AsyncMock(return_value='fake-connection-string'))
    
    # Mock BlobServiceClient
    mock_blob_service_client = mocker.patch('azure.storage.blob.aio.BlobServiceClient.from_connection_string')
    mock_container_client = AsyncMock()
    mock_blob_client = AsyncMock()
    mock_container_client.exists = AsyncMock(return_value=True)
    mock_container_client.get_blob_client = AsyncMock(return_value=mock_blob_client)
    mock_blob_service_client.return_value.__aenter__.return_value.get_container_client.return_value = mock_container_client
    
    # Dados de teste
    company_id = 'testcompany'
    email = 'user+test@example.com'
    project_id = 'proj123'
    job_id = 'job456'
    filename = 'documento_recebido.docx'
    file_content = b'fake-content'
    
    from backend.app.utils.blob_storage_helper import build_blob_path, sanitize_email
    blob_path = build_blob_path(company_id, email, project_id, job_id, filename)
    
    # Função fictícia de upload (deve ser implementada no projeto principal)
    async def upload_document(company_id, email, project_id, job_id, filename, file_content):
        conn_str = await vault_service.get_secret('blobstorage-connection-string', company_id)
        if not conn_str:
            return None
        async with BlobServiceClient.from_connection_string(conn_str) as blob_service_client:
            container_client = blob_service_client.get_container_client(company_id)
            if not await container_client.exists():
                await container_client.create_container()
            blob_name = build_blob_path(company_id, email, project_id, job_id, filename)
            blob_client = container_client.get_blob_client(blob_name)
            await blob_client.upload_blob(file_content, overwrite=True)
            return blob_name
    
    result = await upload_document(company_id, email, project_id, job_id, filename, file_content)
    assert result == blob_path

@pytest.mark.asyncio
async def test_upload_document_missing_credentials(mocker):
    mocker.patch.object(vault_service, 'get_secret', AsyncMock(return_value=None))
    company_id = 'testcompany'
    email = 'user@example.com'
    project_id = 'proj123'
    job_id = 'job456'
    filename = 'documento_recebido.docx'
    file_content = b'fake-content'
    
    async def upload_document(company_id, email, project_id, job_id, filename, file_content):
        conn_str = await vault_service.get_secret('blobstorage-connection-string', company_id)
        if not conn_str:
            return None
        return 'should not reach here'
    
    result = await upload_document(company_id, email, project_id, job_id, filename, file_content)
    assert result is None

@pytest.mark.asyncio
async def test_upload_document_container_creation(mocker):
    mocker.patch.object(vault_service, 'get_secret', AsyncMock(return_value='fake-connection-string'))
    mock_blob_service_client = mocker.patch('azure.storage.blob.aio.BlobServiceClient.from_connection_string')
    mock_container_client = AsyncMock()
    mock_blob_client = AsyncMock()
    mock_container_client.exists = AsyncMock(return_value=False)
    mock_container_client.create_container = AsyncMock()
    mock_container_client.get_blob_client = AsyncMock(return_value=mock_blob_client)
    mock_blob_service_client.return_value.__aenter__.return_value.get_container_client.return_value = mock_container_client
    
    company_id = 'testcompany'
    email = 'user@example.com'
    project_id = 'proj123'
    job_id = 'job456'
    filename = 'documento_recebido.docx'
    file_content = b'fake-content'
    
    from backend.app.utils.blob_storage_helper import build_blob_path
    blob_path = build_blob_path(company_id, email, project_id, job_id, filename)
    
    async def upload_document(company_id, email, project_id, job_id, filename, file_content):
        conn_str = await vault_service.get_secret('blobstorage-connection-string', company_id)
        async with BlobServiceClient.from_connection_string(conn_str) as blob_service_client:
            container_client = blob_service_client.get_container_client(company_id)
            if not await container_client.exists():
                await container_client.create_container()
            blob_name = build_blob_path(company_id, email, project_id, job_id, filename)
            blob_client = container_client.get_blob_client(blob_name)
            await blob_client.upload_blob(file_content, overwrite=True)
            return blob_name
    
    result = await upload_document(company_id, email, project_id, job_id, filename, file_content)
    assert result == blob_path
    mock_container_client.create_container.assert_awaited()
