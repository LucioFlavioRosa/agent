import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from backend.app.services.vault_service import vault_service

from azure.storage.blob.aio import BlobServiceClient

class BlobStorageService:
    def __init__(self, vault_service):
        self.vault_service = vault_service

    async def save_document(self, company_id, project_id, job_id, content, filename, group_id=None):
        # Busca connection string
        conn_str = await self.vault_service.get_secret('blobstorage-connection-string', company_id, group_id)
        if not conn_str:
            raise Exception('Connection string not found')
        container_name = company_id
        blob_path = f"{project_id}/{job_id}/{filename}"
        async with BlobServiceClient.from_connection_string(conn_str) as blob_service_client:
            container_client = blob_service_client.get_container_client(container_name)
            if not await container_client.exists():
                await container_client.create_container()
            blob_client = container_client.get_blob_client(blob_path)
            await blob_client.upload_blob(content, overwrite=True)
        return f"{container_name}/{blob_path}"

@pytest_asyncio.fixture
async def blob_storage_service():
    return BlobStorageService(vault_service)

@pytest.mark.asyncio
async def test_save_document_success(mocker, blob_storage_service):
    # Mock vault_service.get_secret
    mocker.patch.object(blob_storage_service.vault_service, 'get_secret', AsyncMock(return_value='fake_conn_str'))
    # Mock BlobServiceClient
    mock_blob_service_client = AsyncMock()
    mock_container_client = AsyncMock()
    mock_blob_client = AsyncMock()
    mock_container_client.exists.return_value = True
    mock_container_client.get_blob_client.return_value = mock_blob_client
    mock_blob_service_client.get_container_client.return_value = mock_container_client
    patch_blob_service = patch('azure.storage.blob.aio.BlobServiceClient.from_connection_string', return_value=mock_blob_service_client)
    with patch_blob_service:
        result = await blob_storage_service.save_document(
            company_id='comp123',
            project_id='proj456',
            job_id='job789',
            content=b'data',
            filename='documento.docx',
            group_id=None
        )
        assert result == 'comp123/proj456/job789/documento.docx'
        mock_blob_client.upload_blob.assert_awaited_with(b'data', overwrite=True)

@pytest.mark.asyncio
async def test_save_document_vault_failure(mocker, blob_storage_service):
    mocker.patch.object(blob_storage_service.vault_service, 'get_secret', AsyncMock(return_value=None))
    with pytest.raises(Exception) as exc:
        await blob_storage_service.save_document(
            company_id='comp123',
            project_id='proj456',
            job_id='job789',
            content=b'data',
            filename='documento.docx',
            group_id=None
        )
    assert 'Connection string not found' in str(exc.value)

@pytest.mark.asyncio
async def test_save_document_creates_container(mocker, blob_storage_service):
    mocker.patch.object(blob_storage_service.vault_service, 'get_secret', AsyncMock(return_value='fake_conn_str'))
    mock_blob_service_client = AsyncMock()
    mock_container_client = AsyncMock()
    mock_blob_client = AsyncMock()
    mock_container_client.exists.return_value = False
    mock_container_client.get_blob_client.return_value = mock_blob_client
    mock_blob_service_client.get_container_client.return_value = mock_container_client
    patch_blob_service = patch('azure.storage.blob.aio.BlobServiceClient.from_connection_string', return_value=mock_blob_service_client)
    with patch_blob_service:
        await blob_storage_service.save_document(
            company_id='comp123',
            project_id='proj456',
            job_id='job789',
            content=b'data',
            filename='documento.docx',
            group_id=None
        )
        mock_container_client.create_container.assert_awaited()
        mock_blob_client.upload_blob.assert_awaited_with(b'data', overwrite=True)
