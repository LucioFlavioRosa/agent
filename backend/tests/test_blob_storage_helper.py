import pytest
from unittest.mock import AsyncMock, patch

from main import generate_blob_path, save_markdown_report

@pytest.mark.parametrize("company_id,email,project_id,job_id,report_type,filename,expected", [
    ("c1", "user@example.com", "p1", "j1", "epics", "md", "c1/user@example.com/p1/j1/epics.md"),
    ("c2", "another@domain.com", "p2", "j2", "features", "md", "c2/another@domain.com/p2/j2/features.md"),
    ("c3", "", "p3", "j3", "timeline", "md", "c3//p3/j3/timeline.md"),
])
def test_generate_blob_path(company_id, email, project_id, job_id, report_type, filename, expected):
    path = generate_blob_path(company_id, email, project_id, job_id, report_type, filename)
    assert path == expected

@pytest.mark.asyncio
@patch("main.upload_file_to_blob", new_callable=AsyncMock)
async def test_save_markdown_report(mock_upload_file_to_blob):
    blob_conn_str = "fake_conn_str"
    blob_container = "fake_container"
    blob_path = "c1/user@example.com/p1/j1/epics.md"
    report_content = "# Relatório de Teste\n\nConteúdo..."
    await save_markdown_report(blob_conn_str, blob_container, blob_path, report_content)
    mock_upload_file_to_blob.assert_awaited_once_with(blob_conn_str, blob_container, blob_path, report_content.encode("utf-8"))
