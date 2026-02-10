import pytest
from unittest.mock import patch, MagicMock

# Os testes relacionados ao upload de arquivos DOCX foram removidos, pois essa funcionalidade não existe mais no backend.

@pytest.mark.asyncio
def test_lazy_loading_blob_clients(monkeypatch):
    # Testa que o cliente só é criado sob demanda
    from backend.app.services import blob_storage_service
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
