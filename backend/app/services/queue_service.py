import os
import asyncio
import json
import base64
import httpx  # 🚀 IMPORT NOVO (Lembre-se de adicionar no requirements.txt)
from typing import Optional
from azure.storage.queue.aio import QueueClient
from backend.app.services.vault_service import VaultService
from backend.app.services.blob_storage_service import BlobStorageService
from backend.app.services.context_retrieval_service import ContextRetrievalService
from backend.app.services.agent_service import AgentService
from backend.app.services.claude_aws_service import ClaudeAWSService
from backend.app.utils.log_formatter import StructuredLogger

logger = StructuredLogger("queue_service")

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

    # 🚀 NOVO MÉTODO DE NOTIFICAÇÃO
    async def _notificar_backend(self, job_id: str, company_id: str, project_id: str, status: str):
        """
        Envia um POST assíncrono para o Backend avisando que o processamento terminou.
        """
        webhook_url = os.getenv("BACKEND_WEBHOOK_URL", "https://sua-url-do-backend.com/api/webhook/job-status")
        
        if "sua-url-do-backend" in webhook_url:
            logger.log_info_negocio("webhook_ignorado", "URL de webhook não configurada no env, pulando notificação.", job_id=job_id, company_id=company_id)
            return

        payload = {
            "job_id": job_id,
            "company_id": company_id,
            "project_id": project_id,
            "status": status # "done" ou "error"
        }

        logger.log_info_negocio("webhook_iniciado", f"Enviando status '{status}' para o backend", job_id=job_id, company_id=company_id)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload, timeout=15.0)
                response.raise_for_status() 
                logger.log_info_negocio("webhook_sucesso", "Backend notificado com sucesso", job_id=job_id, company_id=company_id)
                
        except Exception as e:
            logger.log_erro("webhook_erro", f"Falha ao notificar backend: {str(e)}", job_id=job_id, company_id=company_id)

    async def process_single_message(self, msg, queue_client: QueueClient, worker_id: int):
        try:
            decoded_str = base64.b64decode(msg.content).decode('utf-8')
            task_data = json.loads(decoded_str)
            job_id = task_data.get('job_id')
            company_id = task_data.get('company_id')
            project_id = task_data.get('project_id')
            group_ids = task_data.get('group_ids')
            blob_path = task_data.get('blob_path')
            
            logger.log_info_negocio("job_recebido_fila", f"Job recebido da fila", job_id=job_id, company_id=company_id, extra={"worker_id": worker_id})
            
            file_bytes = None
            texto_extraido = ""
            if blob_path:
                file_bytes = await self.blob_storage_service.download_document(
                    company_id=company_id,
                    blob_path=blob_path,
                    group_id=group_ids
                )
            
            logger.log_info_negocio("job_inicio_processamento", f"Iniciando processamento do job", job_id=job_id, company_id=company_id, extra={"worker_id": worker_id})
            
            resultado_markdown = await self.agent_service.executar_analise(
                task_payload=task_data,
                texto_extraido=texto_extraido
            )
            
            logger.log_info_negocio("job_finalizado", f"Job finalizado com sucesso", job_id=job_id, company_id=company_id, extra={"worker_id": worker_id})
            
            # 1. Apaga a mensagem da fila para não reprocessar
            await queue_client.delete_message(msg)
            
            # 2. 🚀 Notifica o Backend (Status: done)
            await self._notificar_backend(
                job_id=job_id,
                company_id=company_id,
                project_id=project_id,
                status="done"
            )
            
        except Exception as e:
            logger.log_erro("erro_processamento_job", f"Erro ao processar mensagem: {e}", extra={"worker_id": worker_id})
            
            # 🚀 Tenta extrair os dados da mensagem para avisar o backend do erro!
            try:
                task_data = json.loads(base64.b64decode(msg.content).decode('utf-8'))
                await self._notificar_backend(
                    job_id=task_data.get("job_id"),
                    company_id=task_data.get("company_id"),
                    project_id=task_data.get("project_id"),
                    status="error"
                )
            except Exception:
                pass # Se der erro na leitura do JSON, ignora e segue

    async def _consumer_loop(self, queue_client: QueueClient, worker_id: int):
        logger.log_info_negocio("worker_iniciado", f"Worker-{worker_id} iniciado.", extra={"worker_id": worker_id})
        while True:
            try:
                msg = await self.internal_queue.get()
                await self.process_single_message(msg, queue_client, worker_id)
                self.internal_queue.task_done()
            except asyncio.CancelledError:
                logger.log_info_negocio("worker_cancelado", f"Worker-{worker_id} cancelado.", extra={"worker_id": worker_id})
                break
            except Exception as e:
                logger.log_erro("erro_consumer_loop", f"Erro crítico no loop do consumidor: {e}", extra={"worker_id": worker_id})

    async def start_worker(self):
        logger.log_info_negocio("orquestrador_worker_iniciado", "Orquestrador do Worker iniciado.")
        queue_conn_str = await self.vault_service.get_queue_connection_string()
        if not queue_conn_str:
            logger.log_erro("erro_sem_connection_string_fila", "Abortando worker: Sem connection string da fila.")
            return
        async with QueueClient.from_connection_string(conn_str=queue_conn_str, queue_name=self.queue_name) as queue_client:
            try:
                await queue_client.create_queue()
                logger.log_info_negocio("fila_criada", f"Fila '{self.queue_name}' criada/verificada.")
            except Exception:
                logger.log_info_negocio("fila_existente", f"Fila '{self.queue_name}' já existe ou erro ao criar.")
            workers = [
                asyncio.create_task(self._consumer_loop(queue_client, i))
                for i in range(self.max_concurrent_workers)
            ]
            for i in range(self.max_concurrent_workers):
                logger.log_info_negocio("worker_iniciado", f"Worker-{i} iniciado.", extra={"worker_id": i})
            try:
                while True:
                    messages = queue_client.receive_messages(max_messages=5, visibility_timeout=300)
                    has_messages = False
                    async for msg in messages:
                        has_messages = True
                        logger.log_info_negocio("mensagem_recebida_queue", "Nova mensagem recebida do Azure Queue.")
                        await self.internal_queue.put(msg)
                    if not has_messages:
                        await asyncio.sleep(3)
            except asyncio.CancelledError:
                logger.log_info_negocio("orquestrador_worker_cancelado", "Sinal de desligamento recebido. Parando orquestrador...")
            finally:
                for w in workers:
                    w.cancel()
                await asyncio.gather(*workers, return_exceptions=True)
                logger.log_info_negocio("workers_finalizados", "Todos os workers cancelados e finalizados.")

    async def send_message(self, task_payload: dict) -> bool:
        job_id = task_payload.get('job_id')
        company_id = task_payload.get('company_id')
        logger.log_info_negocio("envio_mensagem_fila", "Enviando mensagem para fila", job_id=job_id, company_id=company_id)
        queue_conn_str = await self.vault_service.get_queue_connection_string()
        if not queue_conn_str:
            logger.log_erro("erro_envio_mensagem_fila", "Falha ao obter conexão da fila do Azure.", job_id=job_id, company_id=company_id)
            raise Exception("Falha ao obter conexão da fila do Azure.")
        async with QueueClient.from_connection_string(conn_str=queue_conn_str, queue_name=self.queue_name) as queue_client:
            message_b64 = base64.b64encode(json.dumps(task_payload).encode('utf-8')).decode('utf-8')
            await queue_client.send_message(message_b64)
            logger.log_info_negocio("mensagem_enviada_fila", "Mensagem enviada para a fila", job_id=job_id, company_id=company_id)
            return True
