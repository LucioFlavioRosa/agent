import asyncio
import json
import base64
import logging
from typing import Optional
from azure.storage.queue.aio import QueueClient
from backend.app.services.vault_service import VaultService

logger = logging.getLogger("mcp_queue_service")

class QueueService:
    def __init__(self, vault_service: VaultService, queue_name: str):
        self.vault_service = vault_service
        self.queue_name = queue_name

    async def process_single_message(self, msg, queue_client):
        try:
            decoded_str = base64.b64decode(msg.content).decode('utf-8')
            task_data = json.loads(decoded_str)
            job_id = task_data.get('job_id')
            logger.info(f"🔥 [QueueService] Iniciando job: {job_id}")
            await asyncio.sleep(2)  # Simulando processamento IA
            await queue_client.delete_message(msg)
            logger.info(f"✅ [QueueService] Job {job_id} finalizado e removido da fila.")
        except Exception as e:
            logger.error(f"❌ [QueueService] Erro ao processar mensagem: {e}")

    async def start_worker(self):
        logger.info("👷 [QueueService] Worker iniciado...")
        queue_conn_str = await self.vault_service.get_queue_connection_string()
        if not queue_conn_str:
            logger.error("❌ [QueueService] Abortando worker: Sem connection string da fila.")
            return
        async with QueueClient.from_connection_string(conn_str=queue_conn_str, queue_name=self.queue_name) as queue_client:
            try:
                await queue_client.create_queue()
            except Exception:
                pass  # Fila já existe
            while True:
                try:
                    messages = queue_client.receive_messages(max_messages=5, visibility_timeout=300)
                    tasks = []
                    async for msg in messages:
                        tasks.append(self.process_single_message(msg, queue_client))
                    if tasks:
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        for idx, result in enumerate(results):
                            if isinstance(result, Exception):
                                logger.error(f"❌ [QueueService] Erro ao processar mensagem #{idx}: {result}")
                    else:
                        await asyncio.sleep(3)  # Nenhuma mensagem, aguarda
                except Exception as e:
                    logger.error(f"❌ [QueueService] Erro no loop do worker: {e}")
                await asyncio.sleep(3)

    async def send_message(self, task_payload: dict) -> bool:
        queue_conn_str = await self.vault_service.get_queue_connection_string()
        if not queue_conn_str:
            raise Exception("Falha ao obter conexão da fila do Azure.")
        async with QueueClient.from_connection_string(conn_str=queue_conn_str, queue_name=self.queue_name) as queue_client:
            message_b64 = base64.b64encode(json.dumps(task_payload).encode('utf-8')).decode('utf-8')
            await queue_client.send_message(message_b64)
            logger.info(f"[QueueService] Mensagem enviada para a fila: job_id={task_payload.get('job_id')}")
            return True

queue_service = QueueService(vault_service, settings.QUEUE_NAME)
