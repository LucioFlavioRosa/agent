import pytest
from unittest.mock import AsyncMock, patch

# Supondo que ReportStorageService está em backend/app/services/report_storage_service.py
from backend.app.services.report_storage_service import ReportStorageService

@pytest.mark.asyncio
@patch("backend.app.services.report_storage_service.BlobStorageService")
@patch("backend.app.services.report_storage_service.vault_service")
async def test_save_complete_report(mock_vault_service, mock_blob_storage_service):
    service = ReportStorageService(mock_blob_storage_service, mock_vault_service)
    mock_blob_storage_service.upload_markdown = AsyncMock()
    mock_blob_storage_service.upload_file = AsyncMock()
    await service.save_report(
        company_id="123",
        email="user@example.com",
        project_id="456",
        job_id="789",
        analysis_type="agent_epics_generator_digital",
        relatorio="# Relatório Epics",
        comentario_extra="Extra comment",
        documento_bytes=b"docxbytes",
        documento_filename="documento_recebido.docx"
    )
    mock_blob_storage_service.upload_markdown.assert_awaited_with("# Relatório Epics", "123/user@example.com/456/789/epics.md")
    mock_blob_storage_service.upload_markdown.assert_awaited_with("Extra comment", "123/user@example.com/456/789/comentario_extra.md")
    mock_blob_storage_service.upload_file.assert_awaited_with(b"docxbytes", "123/user@example.com/456/789/documento_recebido.docx")

@pytest.mark.asyncio
@patch("backend.app.services.report_storage_service.BlobStorageService")
@patch("backend.app.services.report_storage_service.vault_service")
async def test_save_report_without_document(mock_vault_service, mock_blob_storage_service):
    service = ReportStorageService(mock_blob_storage_service, mock_vault_service)
    mock_blob_storage_service.upload_markdown = AsyncMock()
    mock_blob_storage_service.upload_file = AsyncMock()
    await service.save_report(
        company_id="123",
        email="user@example.com",
        project_id="456",
        job_id="789",
        analysis_type="agent_epics_generator_digital",
        relatorio="# Relatório Epics",
        comentario_extra="Extra comment",
        documento_bytes=None,
        documento_filename=None
    )
    mock_blob_storage_service.upload_markdown.assert_awaited_with("# Relatório Epics", "123/user@example.com/456/789/epics.md")
    mock_blob_storage_service.upload_markdown.assert_awaited_with("Extra comment", "123/user@example.com/456/789/comentario_extra.md")
    mock_blob_storage_service.upload_file.assert_not_called()

@pytest.mark.asyncio
@patch("backend.app.services.report_storage_service.BlobStorageService")
@patch("backend.app.services.report_storage_service.vault_service")
async def test_save_report_without_extra_comment(mock_vault_service, mock_blob_storage_service):
    service = ReportStorageService(mock_blob_storage_service, mock_vault_service)
    mock_blob_storage_service.upload_markdown = AsyncMock()
    mock_blob_storage_service.upload_file = AsyncMock()
    await service.save_report(
        company_id="123",
        email="user@example.com",
        project_id="456",
        job_id="789",
        analysis_type="agent_epics_generator_digital",
        relatorio="# Relatório Epics",
        comentario_extra=None,
        documento_bytes=b"docxbytes",
        documento_filename="documento_recebido.docx"
    )
    mock_blob_storage_service.upload_markdown.assert_awaited_with("# Relatório Epics", "123/user@example.com/456/789/epics.md")
    mock_blob_storage_service.upload_file.assert_awaited_with(b"docxbytes", "123/user@example.com/456/789/documento_recebido.docx")

@pytest.mark.asyncio
@patch("backend.app.services.report_storage_service.BlobStorageService")
@patch("backend.app.services.report_storage_service.vault_service")
async def test_invalid_analysis_type(mock_vault_service, mock_blob_storage_service):
    service = ReportStorageService(mock_blob_storage_service, mock_vault_service)
    mock_blob_storage_service.upload_markdown = AsyncMock()
    mock_blob_storage_service.upload_file = AsyncMock()
    with pytest.raises(ValueError):
        await service.save_report(
            company_id="123",
            email="user@example.com",
            project_id="456",
            job_id="789",
            analysis_type="invalid_type",
            relatorio="# Relatório",
            comentario_extra="Extra comment",
            documento_bytes=b"docxbytes",
            documento_filename="documento_recebido.docx"
        )
