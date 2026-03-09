import io
import os
import docx
import json
import httpx
import base64
import asyncio

from typing import Optional
from azure.storage.queue.aio import QueueClient

#from app.services.vault_service import vault_service
#from app.services.blob_storage_service import blob_storage_service
from app.services.context_retrieval_service import ContextRetrievalService
from app.services.bedrock_service import LLMService as BedrockLLMService
from app.services.prototype_service import AgentService
from app.config.agent_mapping import AGENT_CONFIG
from app.utils.log_formatter import StructuredLogger

logger = StructuredLogger("mcp_prototype_queue_service")

class QueueService:
    def __init__(
        self, 
        vault_service,
        blob_storage_service,
        queue_name: str, 
        max_concurrent_workers: int = 5
    ):
        self.vault_service = vault_service
        self.blob_storage_service = blob_storage_service
        self.queue_name = queue_name
        self.max_concurrent_workers = max_concurrent_workers
        self.internal_queue = asyncio.Queue(maxsize=max_concurrent_workers * 2)
        
        # 🚀 1. INICIALIZA O SERVIÇO DA AWS (BEDROCK)
        self.bedrock_service = BedrockLLMService(vault_service=self.vault_service)
        
        # 🚀 2. REGISTRA NO DICIONÁRIO USANDO O NOME QUE ESTÁ NO AGENT_MAPPING
        llm_registry = {
            "bedrock_service": self.bedrock_service
        }
        
        # 🚀 3. INICIALIZA OS SERVIÇOS DO AGENTE
        self.context_retrieval_service = ContextRetrievalService(
            blob_storage_service=self.blob_storage_service
        )
        self.agent_service = AgentService(
            context_retrieval_service=self.context_retrieval_service,
            blob_storage_service=self.blob_storage_service,
            llm_services=llm_registry # Injeta o Bedrock aqui!
        )

    # NOVO MÉTODo: Necessário para o main.py enviar a mensagem
    async def send_message(self, payload: dict):
        queue_conn_str = await self.vault_service.get_secret("queue-connection-string", company_id="default", vault_type="infra", is_global=True)
        if not queue_conn_str:
            raise ValueError("Connection string da fila não encontrada.")
            
        async with QueueClient.from_connection_string(conn_str=queue_conn_str, queue_name=self.queue_name) as queue_client:
            message_bytes = json.dumps(payload).encode('utf-8')
            encoded_msg = base64.b64encode(message_bytes).decode('utf-8')
            await queue_client.send_message(encoded_msg)

    async def _notificar_backend(
        self, 
        job_id: str, 
        company_id: str, 
        project_id: str, 
        status: str,
        category: str,
        blob_path: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Envia o payload EXATO que o JobCompletePayload do FastAPI espera."""
        backend_base_url = os.getenv("BACKEND_WEBHOOK_URL", "http://host.docker.internal:8000").rstrip('/')
        webhook_url = f"{backend_base_url}/internal/jobs/{job_id}/complete"
        
        payload = {
            "project_id": project_id,
            "company_id": company_id,
            "status": status,
            "category": category,
            "blob_path": blob_path,
            "error_message": error_message
        }

        logger.log_info_negocio("webhook_iniciado", f"Chamando webhook: POST {webhook_url}", job_id=job_id, company_id=company_id)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload, timeout=15.0)
                response.raise_for_status() 
                logger.log_info_negocio("webhook_sucesso", f"Backend atualizado com status '{status}'", job_id=job_id, company_id=company_id)
                
        except httpx.HTTPStatusError as exc:
            logger.log_erro("webhook_erro_http", f"O backend rejeitou o webhook. HTTP {exc.response.status_code}", job_id=job_id, company_id=company_id)
        except Exception as e:
            logger.log_erro("webhook_erro_rede", f"Falha de rede ao notificar backend: {str(e)}", job_id=job_id, company_id=company_id)

    async def _extract_text_from_blob(self, company_id: str, blob_path: str, group_id: Optional[str]) -> str:
        """Função auxiliar para baixar o DOCX do Blob e extrair o texto"""
        if not blob_path: return ""
        try:
            file_bytes = await self.blob_storage_service.download_document(
                company_id=company_id, blob_path=blob_path, group_id=group_id
            )
            doc = docx.Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        except Exception as e:
            logger.log_erro("erro_extracao_docx", f"Erro ao ler DOCX do blob {blob_path}: {e}")
            return ""

    async def process_single_message(self, msg, queue_client: QueueClient, worker_id: int):
        try:
            decoded_str = base64.b64decode(msg.content).decode('utf-8')
            task_data = json.loads(decoded_str)
            
            job_id = task_data.get('job_id')
            company_id = task_data.get('company_id')
            project_id = task_data.get('project_id')
            group_id = task_data.get('group_ids') # Vem como string do main.py
            analysis_type = task_data.get("analysis_type", "unknown")
            
            # Caminhos dos arquivos base (podem vir nulos caso o usuário não envie)
            blob_instrucoes = task_data.get('blob_path') 
            blob_identidade = task_data.get('identidade_visual_blob_path')
            
            logger.log_info_negocio("job_recebido_fila", "Job recebido da fila", job_id=job_id, company_id=company_id, extra={"worker_id": worker_id})
            
            # 1. Extração dos textos (Apenas se os arquivos foram enviados)
            texto_instrucoes = await self._extract_text_from_blob(company_id, blob_instrucoes, group_id)
            texto_identidade = await self._extract_text_from_blob(company_id, blob_identidade, group_id)

            logger.log_info_negocio("job_inicio_processamento", "Iniciando processamento com o AgentService", job_id=job_id, company_id=company_id)
            
            # 2. 🚀 DELEGA TUDO PARA O AGENT SERVICE 🚀
            resultado_html = await self.agent_service.executar_analise(
                task_payload=task_data,
                texto_instrucoes=texto_instrucoes,
                texto_identidade=texto_identidade
            )
            
            # 3. Apaga a mensagem da fila pois deu sucesso
            await queue_client.delete_message(msg)
            
            # 4. Descobre o caminho onde o Agente salvou o arquivo para avisar o Maestro
            config_do_agente = AGENT_CONFIG.get(analysis_type, {})
            nome_arquivo_saida = config_do_agente.get("output_filename", "index.html")
            caminho_salvo = f"{company_id}/{project_id}/{job_id}/{nome_arquivo_saida}"
            
            # 5. Notifica o Backend Maestro
            await self._notificar_backend(
                job_id=job_id,
                company_id=company_id,
                project_id=project_id,
                status="done",
                category="prototype", 
                blob_path=caminho_salvo 
            )
            
            logger.log_info_negocio("job_finalizado", f"Job finalizado com sucesso. Salvo em: {caminho_salvo}", job_id=job_id, company_id=company_id)
            
        except Exception as e:
            logger.log_erro("erro_processamento_job", f"Erro ao processar mensagem: {e}", extra={"worker_id": worker_id})
            try:
                task_data = json.loads(base64.b64decode(msg.content).decode('utf-8'))
                await self._notificar_backend(
                    job_id=task_data.get("job_id"),
                    company_id=task_data.get("company_id"),
                    project_id=task_data.get("project_id"),
                    status="error",
                    category="prototype",
                    error_message=str(e)
                )
            except Exception:
                pass

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
        queue_conn_str = await self.vault_service.get_secret("queue-connection-string", company_id="default", vault_type="infra", is_global=True)
        
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
            
            try:
                while True:
                    messages = queue_client.receive_messages(max_messages=5, visibility_timeout=300)
                    has_messages = False
                    async for msg in messages:
                        has_messages = True
                        logger.log_info_negocio("mensagem_recebida_queue", "Nova mensagem recebida.")
                        await self.internal_queue.put(msg)
                    if not has_messages:
                        await asyncio.sleep(3)
            except asyncio.CancelledError:
                logger.log_info_negocio("orquestrador_worker_cancelado", "Sinal de desligamento recebido.")
            finally:
                for w in workers:
                    w.cancel()
                await asyncio.gather(*workers, return_exceptions=True)
                logger.log_info_negocio("workers_finalizados", "Todos os workers finalizados.")
