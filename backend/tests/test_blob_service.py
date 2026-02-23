import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import sys
sys.modules['azure.storage.blob.aio'] = MagicMock()

from backend.app.services.vault_service import vault_service

@pytest_asyncio.fixture
def blob_service_client_mock():
    mock = MagicMock()
    mock.get_container_client.return_value = MagicMock()
    return mock

@pytest.mark.asyncio
async def test_upload_document_success(mocker, blob_service_client_mock):
    # Mock vault_service.get_secret
    mocker.patch.object(vault_service, 'get_secret', AsyncMock(return_value='fake-conn-str'))
    # Mock BlobServiceClient
    mocker.patch('azure.storage.blob.aio.BlobServiceClient.from_connection_string', return_value=blob_service_client_mock)

    # Setup container client
    container_client = blob_service_client_mock.get_container_client.return_value
    container_client.exists = AsyncMock(return_value=True)
    container_client.get_blob_client.return_value = MagicMock()
    blob_client = container_client.get_blob_client.return_value
    blob_client.upload_blob = AsyncMock()

    from backend.app.utils.blob_storage_helper import upload_document
    result = await upload_document(
        company_id='comp123',
        email='user+test@example.com',
        project_id='proj456',
        job_id='job789',
        filename='documento_recebido.docx',
        file_content=b'fake-data'
    )
    assert result == 'comp123/user_test_example_com/proj456/job789/documento_recebido.docx'
    blob_client.upload_blob.assert_awaited_once()

@pytest.mark.asyncio
async def test_upload_document_missing_credentials(mocker):
    mocker.patch.object(vault_service, 'get_secret', AsyncMock(return_value=None))
    from backend.app.utils.blob_storage_helper import upload_document
    result = await upload_document(
        company_id='comp123',
        email='user@example.com',
        project_id='proj456',
        job_id='job789',
        filename='documento_recebido.docx',
        file_content=b'fake-data'
    )
    assert result is None

@pytest.mark.asyncio
async def test_upload_document_container_creation(mocker, blob_service_client_mock):
    mocker.patch.object(vault_service, 'get_secret', AsyncMock(return_value='fake-conn-str'))
    mocker.patch('azure.storage.blob.aio.BlobServiceClient.from_connection_string', return_value=blob_service_client_mock)
    container_client = blob_service_client_mock.get_container_client.return_value
    container_client.exists = AsyncMock(return_value=False)
    container_client.create_container = AsyncMock()
    container_client.get_blob_client.return_value = MagicMock()
    blob_client = container_client.get_blob_client.return_value
    blob_client.upload_blob = AsyncMock()

    from backend.app.utils.blob_storage_helper import upload_document
    result = await upload_document(
        company_id='comp123',
        email='user@example.com',
        project_id='proj456',
        job_id='job789',
        filename='documento_recebido.docx',
        file_content=b'fake-data'
    )
    container_client.create_container.assert_awaited_once()
    assert result == 'comp123/user_example_com/proj456/job789/documento_recebido.docx'
