import pytest
from unittest.mock import AsyncMock, patch

# Supondo que BlobStorageService está em backend/app/services/blob_storage_service.py
from backend.app.services.blob_storage_service import BlobStorageService

@pytest.mark.asyncio
@patch("backend.app.services.blob_storage_service.BlobServiceClient")
async def test_upload_file_success(mock_blob_service_client):
    blob_service = BlobStorageService("connection_string", "container_name")
    mock_container_client = AsyncMock()
    mock_blob_client = AsyncMock()
    mock_blob_service_client.from_connection_string.return_value.__aenter__.return_value.get_container_client.return_value = mock_container_client
    mock_container_client.get_blob_client.return_value = mock_blob_client
    mock_blob_client.upload_blob.return_value = AsyncMock()
    await blob_service.upload_file(b"filebytes", "path/to/file.docx")
    mock_blob_client.upload_blob.assert_awaited_with(b"filebytes", overwrite=True)

@pytest.mark.asyncio
@patch("backend.app.services.blob_storage_service.BlobServiceClient")
async def test_upload_markdown_success(mock_blob_service_client):
    blob_service = BlobStorageService("connection_string", "container_name")
    mock_container_client = AsyncMock()
    mock_blob_client = AsyncMock()
    mock_blob_service_client.from_connection_string.return_value.__aenter__.return_value.get_container_client.return_value = mock_container_client
    mock_container_client.get_blob_client.return_value = mock_blob_client
    mock_blob_client.upload_blob.return_value = AsyncMock()
    await blob_service.upload_markdown("# Markdown Report", "path/to/report.md")
    mock_blob_client.upload_blob.assert_awaited_with(b"# Markdown Report", overwrite=True)

@pytest.mark.asyncio
@patch("backend.app.services.blob_storage_service.BlobServiceClient")
async def test_upload_failure(mock_blob_service_client):
    blob_service = BlobStorageService("connection_string", "container_name")
    mock_container_client = AsyncMock()
    mock_blob_client = AsyncMock()
    mock_blob_service_client.from_connection_string.return_value.__aenter__.return_value.get_container_client.return_value = mock_container_client
    mock_container_client.get_blob_client.return_value = mock_blob_client
    mock_blob_client.upload_blob.side_effect = Exception("Upload failed")
    with pytest.raises(Exception):
        await blob_service.upload_file(b"filebytes", "path/to/file.docx")
