import asyncio
import json
import base64
import logging
from typing import Optional
from azure.storage.queue.aio import QueueClient
from backend.app.services.vault_service import VaultService

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

    async def process_single_message(self, msg, queue_client: QueueClient, worker_id: int):
        """Processa uma única mensagem e a remove da fila do Azure em caso de sucesso."""
        try:
            decoded_str = base64.b64decode(msg.content).decode('utf-8')
            task_data = json.loads(decoded_str)
            
            job_id = task_data.get('job_id')
            company_id = task_data.get('company_id')
            group_ids = task_data.get('group_ids')
            blob_path = task_data.get('blob_path') # O caminho do arquivo que veio lá do main.py
            
            logger.info(f"🔥 [Worker-{worker_id}] Iniciando job: {job_id}")
            
            # 2. ATUALIZAÇÃO: Fazer o download do arquivo para a RAM, se existir
            file_bytes = None
            if blob_path:
                logger.info(f"📥 [Worker-{worker_id}] Baixando arquivo do Blob Storage para memória...")
                file_bytes = await self.blob_storage_service.download_document(
                    company_id=company_id,
                    blob_path=blob_path,
                    group_id=group_ids
                )
                logger.info(f"✅ [Worker-{worker_id}] Download concluído ({len(file_bytes)} bytes).")

            
            # --- SUA LÓGICA DE PROCESSAMENTO (IA, etc) AQUI ---
            # 3. ATUALIZAÇÃO: Agora você tem o file_bytes na mão!
            # Você passará este 'file_bytes' para o seu Agente de IA. 
            # O Agente de IA é quem vai chamar aquela função de extrair o texto do DOCX.
            
            # Exemplo de como seria a chamada para o Agente:
            # await agent_service.analisar_documento(
            #     task_data=task_data, 
            #     file_bytes=file_bytes
            # )
            
            await asyncio.sleep(2)  # Simulando processamento
            # --------------------------------------------------
            
            # Deleta a mensagem após o processamento com sucesso
            await queue_client.delete_message(msg)
            logger.info(f"✅ [Worker-{worker_id}] Job {job_id} finalizado e removido da fila.")
            
        except Exception as e:
            logger.error(f"❌ [Worker-{worker_id}] Erro ao processar mensagem: {e}")

    async def _consumer_loop(self, queue_client: QueueClient, worker_id: int):
        """Loop infinito de cada worker local que consome da fila interna."""
        logger.debug(f"👷 [Worker-{worker_id}] Consumidor iniciado e aguardando tarefas...")
        while True:
            try:
                # Fica aguardando até que o Produtor coloque uma mensagem na fila interna
                msg = await self.internal_queue.get()
                await self.process_single_message(msg, queue_client, worker_id)
                self.internal_queue.task_done()
            except asyncio.CancelledError:
                logger.info(f"🛑 [Worker-{worker_id}] Consumidor encerrando (Cancelado).")
                break
            except Exception as e:
                logger.error(f"❌ [Worker-{worker_id}] Erro crítico no loop do consumidor: {e}")

    async def start_worker(self):
        """Loop principal Produtor que busca mensagens no Azure e alimenta os consumidores."""
        logger.info("🚀 [QueueService] Orquestrador do Worker iniciado...")
        
        queue_conn_str = await self.vault_service.get_queue_connection_string()
        if not queue_conn_str:
            logger.error("❌ [QueueService] Abortando worker: Sem connection string da fila.")
            return

        async with QueueClient.from_connection_string(conn_str=queue_conn_str, queue_name=self.queue_name) as queue_client:
            try:
                await queue_client.create_queue()
            except Exception:
                pass  # Fila já existe

            # Inicia os N workers em background
            workers = [
                asyncio.create_task(self._consumer_loop(queue_client, i))
                for i in range(self.max_concurrent_workers)
            ]

            try:
                while True:
                    # Backpressure: Se a fila interna estiver cheia, aguarda antes de buscar mais no Azure
                    if self.internal_queue.full():
                        await asyncio.sleep(1)
                        continue

                    # Busca mensagens no Azure
                    messages = queue_client.receive_messages(max_messages=5, visibility_timeout=300)
                    has_messages = False
                    
                    async for msg in messages:
                        has_messages = True
                        # Coloca a mensagem na fila interna para o primeiro worker livre pegar
                        await self.internal_queue.put(msg)

                    # Se não vieram mensagens do Azure, dá uma pausa para não afogar a API com requisições vazias
                    if not has_messages:
                        await asyncio.sleep(3)
                        
            except asyncio.CancelledError:
                logger.info("🛑 [QueueService] Sinal de desligamento recebido. Parando orquestrador...")
            finally:
                # Quando o app FastAPI for desligado (lifespan encerra), cancelamos os workers graciosamente
                for w in workers:
                    w.cancel()
                await asyncio.gather(*workers, return_exceptions=True)

    async def send_message(self, task_payload: dict) -> bool:
        queue_conn_str = await self.vault_service.get_queue_connection_string()
        if not queue_conn_str:
            raise Exception("Falha ao obter conexão da fila do Azure.")
            
        async with QueueClient.from_connection_string(conn_str=queue_conn_str, queue_name=self.queue_name) as queue_client:
            message_b64 = base64.b64encode(json.dumps(task_payload).encode('utf-8')).decode('utf-8')
            await queue_client.send_message(message_b64)
            logger.info(f"📨 [QueueService] Mensagem enviada para a fila: job_id={task_payload.get('job_id')}")
            return True
