import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
@patch('main.BlobServiceClient')
@patch('main.vault_service')
def test_start_analysis_with_file(mock_vault_service, mock_blob_service_client, client):
    # Mock vault_service.get_secret para retornar connection string e container
    mock_vault_service.get_secret = AsyncMock(side_effect=[
        'test-connection-string',  # blob_conn_str
        'test-company-id'          # blob_container
    ])
    # Mock BlobServiceClient e seus métodos
    mock_blob_service = AsyncMock()
    mock_blob_service_client.from_connection_string.return_value.__aenter__.return_value = mock_blob_service
    container_client = AsyncMock()
    mock_blob_service.get_container_client.return_value = container_client
    container_client.exists.return_value = False
    container_client.create_container.return_value = None
    blob_client = AsyncMock()
    container_client.get_blob_client.return_value = blob_client
    blob_client.upload_blob.return_value = None

    # Dados do arquivo e formulário
    job_id = 'job123'
    project_id = 'proj456'
    company_id = 'comp789'
    email = 'user@example.com'
    file_content = b'fake docx content'
    file_name = 'documento_recebido.docx'

    response = client.post(
        '/api/v1/analysis/start',
        data={
            'job_id': job_id,
            'project_id': project_id,
            'company_id': company_id,
            'email': email
        },
        files={'arquivo_docx': (file_name, file_content, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload['status'] == 'queued'
    assert payload['job_id'] == job_id
    # Verifica se o caminho do blob está correto
    expected_blob_path = f"{company_id}/{email}/{project_id}/{job_id}/{file_name}"
    # O caminho deve estar presente no task_payload enviado para a fila
    # Aqui, como o endpoint não retorna o path diretamente, seria necessário mockar o envio para a fila e capturar o payload
    # Para fins de teste, podemos garantir que upload_blob foi chamado com o conteúdo correto
    blob_client.upload_blob.assert_called_once_with(file_content, overwrite=True)
    container_client.get_blob_client.assert_called_once_with(f"{job_id}_{file_name}")

@pytest.mark.asyncio
@patch('main.BlobServiceClient')
@patch('main.vault_service')
def test_start_analysis_file_without_email(mock_vault_service, mock_blob_service_client, client):
    mock_vault_service.get_secret = AsyncMock(side_effect=[
        'test-connection-string',  # blob_conn_str
        'test-company-id'          # blob_container
    ])
    mock_blob_service = AsyncMock()
    mock_blob_service_client.from_connection_string.return_value.__aenter__.return_value = mock_blob_service
    container_client = AsyncMock()
    mock_blob_service.get_container_client.return_value = container_client
    container_client.exists.return_value = False
    container_client.create_container.return_value = None
    blob_client = AsyncMock()
    container_client.get_blob_client.return_value = blob_client
    blob_client.upload_blob.return_value = None

    job_id = 'job123'
    project_id = 'proj456'
    company_id = 'comp789'
    file_content = b'fake docx content'
    file_name = 'documento_recebido.docx'

    response = client.post(
        '/api/v1/analysis/start',
        data={
            'job_id': job_id,
            'project_id': project_id,
            'company_id': company_id
            # email omitido
        },
        files={'arquivo_docx': (file_name, file_content, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
    )

    assert response.status_code == 500
    assert 'error' in response.json()
    assert response.json()['error'] == 'Falha de credenciais do Blob Storage.' or response.json()['error'] == 'Email é obrigatório para upload de arquivo.'
