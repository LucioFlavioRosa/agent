import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from backend.app.services.document_storage_service import DocumentStorageService

@pytest.fixture
def blob_service_client_mock():
    return MagicMock()

@pytest.fixture
def document_storage_service(blob_service_client_mock):
    return DocumentStorageService(blob_service_client_mock)

@patch("backend.app.services.document_storage_service.blob_storage_helper.upload_blob", new_callable=AsyncMock)
def test_save_input_document_calls_upload_blob(upload_blob_mock, document_storage_service):
    company_id = "comp123"
    email = "user@example.com"
    project_id = "proj456"
    job_id = "job789"
    filename = "documento_recebido.docx"
    file_content = b"fake_content"
    expected_path = f"{company_id}/{email}/{project_id}/{job_id}/documento_recebido.docx"

    # Run
    result = pytest.run(document_storage_service.save_input_document(
        company_id, email, project_id, job_id, filename, file_content
    ))
    upload_blob_mock.assert_awaited_once_with(document_storage_service.blob_service_client, expected_path, file_content)

@patch("backend.app.services.document_storage_service.blob_storage_helper.upload_blob", new_callable=AsyncMock)
def test_save_extra_comment_creates_markdown(upload_blob_mock, document_storage_service):
    company_id = "comp123"
    email = "user@example.com"
    project_id = "proj456"
    job_id = "job789"
    comentario = "Comentario extra"
    expected_path = f"{company_id}/{email}/{project_id}/{job_id}/comentario_extra.md"
    expected_content = comentario.encode("utf-8")

    result = pytest.run(document_storage_service.save_extra_comment(
        company_id, email, project_id, job_id, comentario
    ))
    upload_blob_mock.assert_awaited_once_with(document_storage_service.blob_service_client, expected_path, expected_content)

@patch("backend.app.services.document_storage_service.blob_storage_helper.upload_blob", new_callable=AsyncMock)
def test_save_analysis_report_various_types(upload_blob_mock, document_storage_service):
    company_id = "comp123"
    email = "user@example.com"
    project_id = "proj456"
    job_id = "job789"
    report_content = "Relatorio gerado"
    for analysis_type, report_name in [
        ("agent_epics_generator_digital", "epics.md"),
        ("agent_features_generator_digital", "features.md"),
        ("agent_timeline_generator_digital", "timeline.md"),
        ("agent_risks_generator_digital", "risks.md")
    ]:
        expected_path = f"{company_id}/{email}/{project_id}/{job_id}/{report_name}"
        result = pytest.run(document_storage_service.save_analysis_report(
            company_id, email, project_id, job_id, analysis_type, report_content
        ))
        upload_blob_mock.assert_awaited_with(document_storage_service.blob_service_client, expected_path, report_content.encode("utf-8"))
