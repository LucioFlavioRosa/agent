import asyncio
import json
import base64
import logging
from typing import Optional
from azure.storage.queue.aio import QueueClient
from backend.app.services.vault_service import VaultService
from backend.app.services.blob_storage_service import BlobStorageService

# Importamos os serviços do Agente e de Contexto
from backend.app.services.context_retrieval_service import ContextRetrievalService
from backend.app.services.agent_service import AgentService

# 🚀 NOVO 1: Importamos os provedores de LLM
# Crie este arquivo/classe depois para implementar a chamada real para a AWS
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
        
        # 🚀 NOVO 2: Instanciar os provedores de LLM
        # Passamos o vault para ele caso ele precise buscar chaves da AWS lá
        self.claude_service = ClaudeAWSService(vault_service=self.vault_service)
        
        # 🚀 NOVO 3: Criar o "Registro de LLMs"
        # As chaves deste dicionário DEVEM bater exatamente com a string "service" no seu AGENT_CONFIG
        llm_registry = {
            "claude_aws_service": self.claude_service,
            # "azure_openai_service": AzureOpenAIService(...) -> Para o futuro!
        }

        # Instanciamos a inteligência de Contexto
        self.context_retrieval_service = ContextRetrievalService(
            blob_storage_service=self.blob_storage_service
        )
        
        # 🚀 NOVO 4: Instanciamos o Agente passando o Registro de LLMs
        self.agent_service = AgentService(
            context_retrieval_service=self.context_retrieval_service,
            llm_services=llm_registry
        )

    async def process_single_message(self, msg, queue_client: QueueClient, worker_id: int):
        """Processa uma única mensagem e a remove da fila do Azure em caso de sucesso."""
        try:
            decoded_str = base64.b64decode(msg.content).decode('utf-8')
            task_data = json.loads(decoded_str)
            
            job_id = task_data.get('job_id')
            company_id = task_data.get('company_id')
            group_ids = task_data.get('group_ids')
            blob_path = task_data.get('blob_path')
            
            logger.info(f"🔥 [Worker-{worker_id}] Iniciando job: {job_id}")
            
            # Baixa o arquivo ATUAL (o .docx que o usuário enviou) para a RAM, se existir
            file_bytes = None
            texto_extraido = ""
            if blob_path:
                logger.info(f"📥 [Worker-{worker_id}] Baixando documento atual do Blob Storage para memória...")
                file_bytes = await self.blob_storage_service.download_document(
                    company_id=company_id,
                    blob_path=blob_path,
                    group_id=group_ids
                )
                logger.info(f"✅ [Worker-{worker_id}] Download concluído ({len(file_bytes)} bytes).")
                
                # Supondo que você tem uma função no AgentService para extrair texto do DOCX:
                # texto_extraido = await self.agent_service.extrair_texto_docx(file_bytes)

            
            # Chamar o Agente de IA com o payload completo
            logger.info(f"🧠 [Worker-{worker_id}] Iniciando análise com IA...")
            
            resultado_markdown = await self.agent_service.executar_analise(
                task_payload=task_data,
                texto_extraido=texto_extraido
            )
            
            # (Futuro) Aqui você vai salvar 'resultado_markdown' de volta no Blob Storage 
            # com o nome do output_filename e chamar o Webhook avisando que terminou.
            
            # Deleta a mensagem após o processamento com sucesso
            await queue_client.delete_message(msg)
            logger.info(f"✅ [Worker-{worker_id}] Job {job_id} finalizado e removido da fila.")
            
        except Exception as e:
            logger.error(f"❌ [Worker-{worker_id}] Erro ao processar mensagem: {e}")
            # Lógica de Retry/Dead Letter Queue entraria aqui

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
