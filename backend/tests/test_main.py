import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from main import app

@pytest_asyncio.fixture
async def client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_start_analysis_with_file_upload(mocker):
    # Mock BlobStorageService.save_document
    mock_save_document = AsyncMock(return_value='comp123/proj456/job789/documento.docx')
    patch_blob_service = patch('main.BlobStorageService.save_document', mock_save_document)
    # Mock QueueClient
    mock_queue_client = AsyncMock()
    patch_queue_client = patch('azure.storage.queue.aio.QueueClient.from_connection_string', return_value=mock_queue_client)
    with patch_blob_service, patch_queue_client:
        with TestClient(app) as client:
            data = {
                'job_id': 'job789',
                'project_id': 'proj456',
                'company_id': 'comp123',
                'group_ids': 'group1',
                'email': 'user@example.com',
                'nome_projeto': 'Projeto Teste',
                'analysis_type': 'llm',
                'branch': 'main',
                'repository': 'repo.git',
                'comentario_extra': 'Teste'
            }
            file_content = b'Test file content'
            response = client.post(
                '/api/v1/analysis/start',
                data=data,
                files={'arquivo_docx': ('documento.docx', file_content, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            )
            assert response.status_code == 202
            assert response.json()['status'] == 'queued'
            mock_save_document.assert_awaited_with(
                'comp123', 'proj456', 'job789', file_content, 'documento.docx', 'group1'
            )
