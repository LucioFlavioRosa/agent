import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from backend.app.services.queue_service import QueueService

@pytest.mark.asyncio
async def test_process_single_message_success():
    queue_service = QueueService()
    mock_queue_client = AsyncMock()
    mock_message = MagicMock()
    mock_message.content = b'dGVzdA=='  # base64 for 'test'
    mock_message.id = 'msg-id'
    
    # Simular processamento sem exceção
    with patch('backend.app.services.queue_service.QueueService._process_task', new=AsyncMock()) as mock_process_task:
        await queue_service.process_single_message(mock_queue_client, mock_message)
        mock_process_task.assert_awaited_once_with(mock_message)
        mock_queue_client.delete_message.assert_awaited_once_with(mock_message)

@pytest.mark.asyncio
async def test_process_single_message_exception():
    queue_service = QueueService()
    mock_queue_client = AsyncMock()
    mock_message = MagicMock()
    mock_message.content = b'dGVzdA=='
    mock_message.id = 'msg-id'
    
    # Simular exceção durante processamento
    with patch('backend.app.services.queue_service.QueueService._process_task', new=AsyncMock(side_effect=Exception('fail'))):
        await queue_service.process_single_message(mock_queue_client, mock_message)
        # delete_message não deve ser chamado em caso de falha
        mock_queue_client.delete_message.assert_not_awaited()

@pytest.mark.asyncio
async def test_send_message_success():
    queue_service = QueueService()
    payload = {"job_id": "123", "data": "abc"}
    mock_queue_client = AsyncMock()
    mock_vault_service = AsyncMock()
    mock_vault_service.get_queue_connection_string.return_value = 'conn-string'
    
    with patch('backend.app.services.queue_service.QueueService._get_queue_client', return_value=mock_queue_client):
        with patch('backend.app.services.queue_service.vault_service', mock_vault_service):
            await queue_service.send_message(payload)
            mock_queue_client.send_message.assert_awaited()
            sent_arg = mock_queue_client.send_message.call_args[0][0]
            import base64, json
            decoded = json.loads(base64.b64decode(sent_arg).decode('utf-8'))
            assert decoded == payload

@pytest.mark.asyncio
async def test_send_message_fail_connection_string():
    queue_service = QueueService()
    payload = {"job_id": "123", "data": "abc"}
    mock_vault_service = AsyncMock()
    mock_vault_service.get_queue_connection_string.return_value = None
    
    with patch('backend.app.services.queue_service.vault_service', mock_vault_service):
        with pytest.raises(RuntimeError):
            await queue_service.send_message(payload)

@pytest.mark.asyncio
async def test_start_worker_parallel_processing():
    queue_service = QueueService()
    mock_queue_client = AsyncMock()
    messages = [MagicMock(), MagicMock(), MagicMock()]
    messages[0].content = b'dGVzdDE='  # test1
    messages[1].content = b'dGVzdDI='  # test2
    messages[2].content = b'dGVzdDM='  # test3
    
    # Simular receive_messages retornando 3 mensagens
    mock_queue_client.receive_messages.return_value = iter(messages)
    
    # Simular _process_task: 1 falha, 2 sucesso
    async def fake_process_task(msg):
        if msg == messages[0]:
            raise Exception('fail')
        await asyncio.sleep(0.01)
    
    with patch('backend.app.services.queue_service.QueueService._process_task', new=fake_process_task):
        with patch('backend.app.services.queue_service.QueueService._get_queue_client', return_value=mock_queue_client):
            # Chamar start_worker e garantir que todas as mensagens são processadas
            await queue_service.start_worker()
            # delete_message só chamado para mensagens que não falharam
            assert mock_queue_client.delete_message.await_count == 2
