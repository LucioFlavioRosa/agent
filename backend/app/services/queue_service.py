import asyncio
import json
import base64
import logging
from typing import Optional
from azure.storage.queue.aio import QueueClient
from backend.app.services.vault_service import VaultService
from backend.app.services.blob_storage_service import BlobStorageService
from backend.app.services.context_retrieval_service import ContextRetrievalService
from backend.app.services.agent_service import AgentService
from backend.app.services.claude_aws_service import ClaudeAWSService 

logger = logging.getLogger("mcp_queue_service")

class QueueService:
    def __init__(
        self, 
        vault_service: VaultService, 
        blob_storage_service: BlobStorageService, 
        queue_name: str, 
        max_concurrent_workers: int = 5
    ):
        self.vault_service = vault_service
        self.blob_storage_service = blob_storage_service
        self.queue_name = queue_name
        self.max_concurrent_workers = max_concurrent_workers
        self.internal_queue = asyncio.Queue(maxsize=max_concurrent_workers * 2)
        self.claude_service = ClaudeAWSService(vault_service=self.vault_service)
        llm_registry = {
            "claude_aws_service": self.claude_service,
        }
        self.context_retrieval_service = ContextRetrievalService(
            blob_storage_service=self.blob_storage_service
        )
        self.agent_service = AgentService(
            context_retrieval_service=self.context_retrieval_service,
            blob_storage_service=self.blob_storage_service,
            llm_services=llm_registry
        )

    async def process_single_message(self, msg, queue_client: QueueClient, worker_id: int):
        try:
            logger.info(f"[QueueService] [Worker-{worker_id}] process_single_message chamado. Decodificando mensagem da fila.")
            decoded_str = base64.b64decode(msg.content).decode('utf-8')
            logger.debug(f"[QueueService] [Worker-{worker_id}] Mensagem decodificada: {decoded_str}")
            task_data = json.loads(decoded_str)
            logger.info(f"[QueueService] [Worker-{worker_id}] Payload extraído: job_id='{task_data.get('job_id')}', company_id='{task_data.get('company_id')}', group_ids='{task_data.get('group_ids')}', blob_path='{task_data.get('blob_path')}'")
            job_id = task_data.get('job_id')
            company_id = task_data.get('company_id')
            group_ids = task_data.get('group_ids')
            blob_path = task_data.get('blob_path')
            logger.info(f"[QueueService] [Worker-{worker_id}] Iniciando job: job_id='{job_id}', company_id='{company_id}', group_ids='{group_ids}', blob_path='{blob_path}'")
            file_bytes = None
            texto_extraido = ""
            if blob_path:
                logger.info(f"[QueueService] [Worker-{worker_id}] Baixando documento atual do Blob Storage para memória...")
                file_bytes = await self.blob_storage_service.download_document(
                    company_id=company_id,
                    blob_path=blob_path,
                    group_id=group_ids
                )
                logger.info(f"[QueueService] [Worker-{worker_id}] Download do documento concluído ({len(file_bytes)} bytes).")
            logger.info(f"[QueueService] [Worker-{worker_id}] Iniciando análise com IA...")
            resultado_markdown = await self.agent_service.executar_analise(
                task_payload=task_data,
                texto_extraido=texto_extraido
            )
            logger.info(f"[QueueService] [Worker-{worker_id}] Análise IA concluída para job_id='{job_id}'.")
            await queue_client.delete_message(msg)
            logger.info(f"[QueueService] [Worker-{worker_id}] Job '{job_id}' finalizado e removido da fila.")
        except Exception as e:
            logger.error(f"[QueueService] [Worker-{worker_id}] Erro ao processar mensagem: {e}", exc_info=True)

    async def _consumer_loop(self, queue_client: QueueClient, worker_id: int):
        logger.info(f"[QueueService] [Worker-{worker_id}] _consumer_loop iniciado. Aguardando tarefas...")
        while True:
            try:
                msg = await self.internal_queue.get()
                logger.info(f"[QueueService] [Worker-{worker_id}] Mensagem retirada da fila interna para processamento.")
                await self.process_single_message(msg, queue_client, worker_id)
                self.internal_queue.task_done()
                logger.info(f"[QueueService] [Worker-{worker_id}] Processamento da mensagem finalizado.")
            except asyncio.CancelledError:
                logger.info(f"[QueueService] [Worker-{worker_id}] Consumidor encerrando (Cancelado).")
                break
            except Exception as e:
                logger.error(f"[QueueService] [Worker-{worker_id}] Erro crítico no loop do consumidor: {e}", exc_info=True)

    async def start_worker(self):
        logger.info("[QueueService] Orquestrador do Worker iniciado.")
        queue_conn_str = await self.vault_service.get_queue_connection_string()
        if not queue_conn_str:
            logger.error("[QueueService] Abortando worker: Sem connection string da fila.")
            return
        logger.info("[QueueService] Connection string da fila obtida com sucesso.")
        async with QueueClient.from_connection_string(conn_str=queue_conn_str, queue_name=self.queue_name) as queue_client:
            try:
                await queue_client.create_queue()
                logger.info(f"[QueueService] Fila '{self.queue_name}' criada/verificada com sucesso.")
            except Exception:
                logger.info(f"[QueueService] Fila '{self.queue_name}' já existe ou erro ao criar.")
            workers = [
                asyncio.create_task(self._consumer_loop(queue_client, i))
                for i in range(self.max_concurrent_workers)
            ]
            for i in range(self.max_concurrent_workers):
                logger.info(f"[QueueService] Worker-{i} iniciado.")
            try:
                while True:
                    if self.internal_queue.full():
                        logger.info("[QueueService] Fila interna cheia. Aguardando para buscar mais mensagens.")
                        await asyncio.sleep(1)
                        continue
                    messages = queue_client.receive_messages(max_messages=5, visibility_timeout=300)
                    has_messages = False
                    async for msg in messages:
                        has_messages = True
                        logger.info("[QueueService] Nova mensagem recebida do Azure Queue. Colocando na fila interna.")
                        await self.internal_queue.put(msg)
                    if not has_messages:
                        logger.info("[QueueService] Nenhuma mensagem recebida do Azure Queue. Pausando por 3 segundos.")
                        await asyncio.sleep(3)
            except asyncio.CancelledError:
                logger.info("[QueueService] Sinal de desligamento recebido. Parando orquestrador...")
            finally:
                for w in workers:
                    w.cancel()
                await asyncio.gather(*workers, return_exceptions=True)
                logger.info("[QueueService] Todos os workers cancelados e finalizados.")

    async def send_message(self, task_payload: dict) -> bool:
        logger.info(f"[QueueService] send_message chamado. Enviando mensagem para fila: job_id='{task_payload.get('job_id')}', company_id='{task_payload.get('company_id')}'")
        queue_conn_str = await self.vault_service.get_queue_connection_string()
        if not queue_conn_str:
            logger.error("[QueueService] Falha ao obter conexão da fila do Azure.")
            raise Exception("Falha ao obter conexão da fila do Azure.")
        async with QueueClient.from_connection_string(conn_str=queue_conn_str, queue_name=self.queue_name) as queue_client:
            message_b64 = base64.b64encode(json.dumps(task_payload).encode('utf-8')).decode('utf-8')
            await queue_client.send_message(message_b64)
            logger.info(f"[QueueService] Mensagem enviada para a fila: job_id='{task_payload.get('job_id')}', company_id='{task_payload.get('company_id')}'")
            return True
