import io
import pytest
from unittest.mock import Mock, patch

# Supondo que upload_docx_to_blob esteja em backend/services/blob_uploader.py
from backend.services.blob_uploader import upload_docx_to_blob

def test_upload_docx_to_blob_success():
    mock_blob_service = Mock()
    mock_blob_service.upload_blob.return_value = "https://fake.blob.core.windows.net/container/path/to/file.docx"
    file_stream = io.BytesIO(b"fake docx content")
    usuario_executor = "usuario1"
    projeto = "projetoX"
    analysis_name = "analise123"
    url = upload_docx_to_blob(
        blob_service=mock_blob_service,
        file_stream=file_stream,
        usuario_executor=usuario_executor,
        projeto=projeto,
        analysis_name=analysis_name
    )
    expected_path = f"{usuario_executor}/{projeto}/arquivos_recebidos/docx/{analysis_name}.docx"
    mock_blob_service.upload_blob.assert_called_once_with(expected_path, file_stream)
    assert url == "https://fake.blob.core.windows.net/container/path/to/file.docx"

def test_upload_docx_to_blob_failure():
    mock_blob_service = Mock()
    mock_blob_service.upload_blob.side_effect = Exception("Upload failed!")
    file_stream = io.BytesIO(b"fake docx content")
    with pytest.raises(Exception) as excinfo:
        upload_docx_to_blob(
            blob_service=mock_blob_service,
            file_stream=file_stream,
            usuario_executor="usuario1",
            projeto="projetoX",
            analysis_name="analise123"
        )
    assert "Upload failed!" in str(excinfo.value)
