import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from backend.app.services.blob_storage_service import BlobStorageService

@pytest.mark.asyncio
class TestBlobStorageService:
    @patch('backend.app.services.blob_storage_service.BlobServiceClient')
    @patch('backend.app.services.blob_storage_service.build_blob_path')
    async def test_upload_document_success(self, mock_build_blob_path, mock_blob_service_client):
        mock_build_blob_path.return_value = '123/sanitized/456/789/file.docx'
        mock_blob_service_client.from_connection_string.return_value.__aenter__.return_value = mock_blob_service_client
        container_client = MagicMock()
        container_client.exists = AsyncMock(return_value=True)
        blob_client = MagicMock()
        blob_client.upload_blob = AsyncMock()
        mock_blob_service_client.get_container_client.return_value = container_client
        container_client.get_blob_client.return_value = blob_client

        service = BlobStorageService('conn_str', 'container')
        result = await service.upload_document('123', 'email@ex.com', '456', '789', b'data', 'file.docx')
        blob_client.upload_blob.assert_awaited_once_with(b'data', overwrite=True)
        assert result == '123/sanitized/456/789/file.docx'

    @patch('backend.app.services.blob_storage_service.BlobServiceClient')
    @patch('backend.app.services.blob_storage_service.build_blob_path')
    async def test_upload_document_creates_container_if_not_exists(self, mock_build_blob_path, mock_blob_service_client):
        mock_build_blob_path.return_value = 'cid/sanitized/pid/jid/file.docx'
        mock_blob_service_client.from_connection_string.return_value.__aenter__.return_value = mock_blob_service_client
        container_client = MagicMock()
        container_client.exists = AsyncMock(return_value=False)
        container_client.create_container = AsyncMock()
        blob_client = MagicMock()
        blob_client.upload_blob = AsyncMock()
        mock_blob_service_client.get_container_client.return_value = container_client
        container_client.get_blob_client.return_value = blob_client

        service = BlobStorageService('conn_str', 'container')
        await service.upload_document('cid', 'email@ex.com', 'pid', 'jid', b'data', 'file.docx')
        container_client.create_container.assert_awaited_once()
        blob_client.upload_blob.assert_awaited_once_with(b'data', overwrite=True)

    @patch('backend.app.services.blob_storage_service.BlobServiceClient')
    @patch('backend.app.services.blob_storage_service.build_blob_path')
    async def test_upload_document_handles_upload_error(self, mock_build_blob_path, mock_blob_service_client):
        mock_build_blob_path.return_value = 'cid/sanitized/pid/jid/file.docx'
        mock_blob_service_client.from_connection_string.return_value.__aenter__.return_value = mock_blob_service_client
        container_client = MagicMock()
        container_client.exists = AsyncMock(return_value=True)
        blob_client = MagicMock()
        blob_client.upload_blob = AsyncMock(side_effect=Exception('upload error'))
        mock_blob_service_client.get_container_client.return_value = container_client
        container_client.get_blob_client.return_value = blob_client

        service = BlobStorageService('conn_str', 'container')
        with pytest.raises(Exception) as exc:
            await service.upload_document('cid', 'email@ex.com', 'pid', 'jid', b'data', 'file.docx')
        assert 'upload error' in str(exc.value)
