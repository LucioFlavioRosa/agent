import pytest
import asyncio
from unittest.mock import AsyncMock, patch

import sys
sys.modules['azure.storage.blob.aio'] = __import__('types')

from backend.app.services.blob_storage_service import BlobStorageService, BlobStorageConnectionError, BlobUploadError

@pytest.mark.asyncio
async def test_upload_document_success(mocker):
    mock_vault_service = AsyncMock()
    mock_vault_service.get_secret.return_value = 'fake-conn-string'

    mock_blob_service_client = AsyncMock()
    mock_container_client = AsyncMock()
    mock_blob_client = AsyncMock()

    mock_blob_service_client.get_container_client.return_value = mock_container_client
    mock_container_client.exists.return_value = True
    mock_container_client.get_blob_client.return_value = mock_blob_client
    mock_blob_client.upload_blob.return_value = None

    mocker.patch('backend.app.services.blob_storage_service.BlobServiceClient.from_connection_string', return_value=mock_blob_service_client)

    blob_service = BlobStorageService(mock_vault_service)
    file_content = b'dummy'
    file_name = 'documento_recebido.docx'
    company_id = 'comp123'
    project_id = 'proj456'
    job_id = 'job789'

    path = await blob_service.upload_document(file_content, file_name, company_id, project_id, job_id)
    assert path == f'{company_id}/{project_id}/{job_id}/{file_name}'
    mock_vault_service.get_secret.assert_called_once_with('blobstorage-connection-string', company_id)
    mock_blob_service_client.get_container_client.assert_called_once_with(company_id)
    mock_container_client.get_blob_client.assert_called_once_with(f'{project_id}/{job_id}/{file_name}')
    mock_blob_client.upload_blob.assert_called_once_with(file_content, overwrite=True)

@pytest.mark.asyncio
async def test_upload_document_vault_failure(mocker):
    mock_vault_service = AsyncMock()
    mock_vault_service.get_secret.return_value = None
    blob_service = BlobStorageService(mock_vault_service)
    with pytest.raises(BlobStorageConnectionError):
        await blob_service.upload_document(b'dummy', 'doc.docx', 'comp', 'proj', 'job')

@pytest.mark.asyncio
async def test_upload_document_blob_failure(mocker):
    mock_vault_service = AsyncMock()
    mock_vault_service.get_secret.return_value = 'fake-conn-string'
    mock_blob_service_client = AsyncMock()
    mock_container_client = AsyncMock()
    mock_blob_client = AsyncMock()
    mock_blob_client.upload_blob.side_effect = Exception('upload failed')
    mock_blob_service_client.get_container_client.return_value = mock_container_client
    mock_container_client.exists.return_value = True
    mock_container_client.get_blob_client.return_value = mock_blob_client

    mocker.patch('backend.app.services.blob_storage_service.BlobServiceClient.from_connection_string', return_value=mock_blob_service_client)
    blob_service = BlobStorageService(mock_vault_service)
    with pytest.raises(BlobUploadError):
        await blob_service.upload_document(b'dummy', 'doc.docx', 'comp', 'proj', 'job')

@pytest.mark.asyncio
async def test_upload_document_creates_container(mocker):
    mock_vault_service = AsyncMock()
    mock_vault_service.get_secret.return_value = 'fake-conn-string'
    mock_blob_service_client = AsyncMock()
    mock_container_client = AsyncMock()
    mock_blob_client = AsyncMock()
    mock_container_client.exists.return_value = False
    mock_container_client.create_container.return_value = None
    mock_container_client.get_blob_client.return_value = mock_blob_client
    mock_blob_client.upload_blob.return_value = None
    mock_blob_service_client.get_container_client.return_value = mock_container_client

    mocker.patch('backend.app.services.blob_storage_service.BlobServiceClient.from_connection_string', return_value=mock_blob_service_client)
    blob_service = BlobStorageService(mock_vault_service)
    await blob_service.upload_document(b'dummy', 'doc.docx', 'comp', 'proj', 'job')
    mock_container_client.create_container.assert_called_once()

@pytest.mark.asyncio
async def test_upload_document_path_structure(mocker):
    mock_vault_service = AsyncMock()
    mock_vault_service.get_secret.return_value = 'fake-conn-string'
    mock_blob_service_client = AsyncMock()
    mock_container_client = AsyncMock()
    mock_blob_client = AsyncMock()
    mock_container_client.exists.return_value = True
    mock_container_client.get_blob_client.return_value = mock_blob_client
    mock_blob_client.upload_blob.return_value = None
    mock_blob_service_client.get_container_client.return_value = mock_container_client

    mocker.patch('backend.app.services.blob_storage_service.BlobServiceClient.from_connection_string', return_value=mock_blob_service_client)
    blob_service = BlobStorageService(mock_vault_service)
    file_name = 'report.pdf'
    company_id = 'c1'
    project_id = 'p2'
    job_id = 'j3'
    path = await blob_service.upload_document(b'dummy', file_name, company_id, project_id, job_id)
    assert path == f'{company_id}/{project_id}/{job_id}/{file_name}'
