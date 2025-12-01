import pytest
from unittest.mock import patch, MagicMock
from fastapi import BackgroundTasks, UploadFile, HTTPException
from backend.app.services import blob_storage_service

class DummyUploadFile:
    def __init__(self, filename, content):
        self.filename = filename
        self.file = MagicMock()
        self.file.read = MagicMock(return_value=content)
        self.file.seek = MagicMock()

@pytest.mark.asyncio
def test_upload_with_background_tasks_success():
    # Simula leitura de bytes antes de passar para background
    dummy_content = b"dummy docx content"
    dummy_file = DummyUploadFile("test.docx", dummy_content)
    background_tasks = BackgroundTasks()
    with patch("backend.app.services.blob_storage_service.BlobServiceClient") as mock_blob_client:
        mock_blob_instance = MagicMock()
        mock_blob_client.from_connection_string.return_value = mock_blob_instance
        mock_container_client = MagicMock()
        mock_blob_instance.get_container_client.return_value = mock_container_client
        mock_blob_client_obj = MagicMock()
        mock_container_client.get_blob_client.return_value = mock_blob_client_obj
        mock_blob_client_obj.url = "https://dummy.blob.core.windows.net/arquivos/test.docx"
        # Chama função
        result = await blob_storage_service.upload_docx_to_blob(
            dummy_file, "dummy-folder", "test.docx", background_tasks
        )
        assert result == "https://dummy.blob.core.windows.net/arquivos/test.docx"
        # Verifica que o upload foi agendado
        assert len(background_tasks.tasks) == 1

@pytest.mark.asyncio
def test_upload_with_empty_connection_string(monkeypatch):
    # Simula settings sem connection string
    monkeypatch.setattr(blob_storage_service, "settings", MagicMock(AZURE_STORAGE_CONNECTION_STRING=""))
    with pytest.raises(RuntimeError):
        # Força a inicialização do BlobServiceClient
        blob_storage_service.BlobServiceClient.from_connection_string("")

@pytest.mark.asyncio
def test_lazy_loading_blob_clients(monkeypatch):
    # Testa que o cliente só é criado sob demanda
    monkeypatch.setattr(blob_storage_service, "settings", MagicMock(AZURE_STORAGE_CONNECTION_STRING="dummy-conn-str", AZURE_STORAGE_CONTAINER_NAME="arquivos"))
    with patch("backend.app.services.blob_storage_service.BlobServiceClient") as mock_blob_client:
        mock_blob_instance = MagicMock()
        mock_blob_client.from_connection_string.return_value = mock_blob_instance
        mock_container_client = MagicMock()
        mock_blob_instance.get_container_client.return_value = mock_container_client
        # Chama função que deveria criar cliente sob demanda
        blob_service_client = blob_storage_service.BlobServiceClient.from_connection_string("dummy-conn-str")
        assert blob_service_client is mock_blob_instance
        container_client = blob_service_client.get_container_client("arquivos")
        assert container_client is mock_container_client
