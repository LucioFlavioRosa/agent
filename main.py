import asyncio
import json
import base64
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import JSONResponse
from azure.storage.queue.aio import QueueClient
from azure.storage.blob.aio import BlobServiceClient

logger = logging.getLogger("mcp_worker")

# Instância global do VaultService
vault_urls = [
    settings.AZURE_INFRA_VAULT_URL,
    settings.AZURE_LLM_VAULT_URL,
    settings.AZURE_PROJECTS_VAULT_URL
]
vault_service = VaultService(vault_urls)

# --- WORKER ---
async def process_queue_messages():
    logger.info("👷 Worker iniciado...")
    
    queue_conn_str = await vault_service.get_queue_connection_string()
    if not queue_conn_str:
        logger.error("❌ Abortando worker: Sem connection string da fila.")
        return

    # Usando async with para o QueueClient
    async with QueueClient.from_connection_string(conn_str=queue_conn_str, queue_name=settings.QUEUE_NAME) as queue_client:
        try:
            await queue_client.create_queue()
        except Exception:
            pass # Fila já existe

        while True:
            try:
                messages = queue_client.receive_messages(max_messages=5, visibility_timeout=300)
                async for msg in messages:
                    decoded_str = base64.b64decode(msg.content).decode('utf-8')
                    task_data = json.loads(decoded_str)
                    
                    logger.info(f"🔥 Iniciando job: {task_data.get('job_id')}")
                    await asyncio.sleep(2) # Simulando IA
                    
                    await queue_client.delete_message(msg)
                    logger.info(f"✅ Job {task_data.get('job_id')} finalizado e removido da fila.")
            except Exception as e:
                logger.error(f"Erro no loop do worker: {e}")
            
            await asyncio.sleep(3)

# --- LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_task = asyncio.create_task(process_queue_messages())
    yield
    worker_task.cancel()
    # Espera a tarefa cancelar graciosamente
    try:
        await worker_task
    except asyncio.CancelledError:
        logger.info("👷 Worker parado com sucesso.")

app = FastAPI(title="MCP Queue Worker", lifespan=lifespan)

# --- ENDPOINTS ---
@app.post("/api/v1/analysis/start")
async def start_analysis(
    job_id: str = Form(...),
    company_id: str = Form(...),
    group_ids: Optional[str] = Form(None),
    arquivo_docx: Optional[UploadFile] = File(None)
    # ... adicione os outros campos Form aqui ...
):
    blob_temp_path = None
    
    # Busca credenciais do Azure Blob no Key Vault
    blob_conn_str = await vault_service.get_secret('blobstorage-connection-string', company_id, group_ids)
    blob_container = await vault_service.get_secret('blobstorage-container-name', company_id, group_ids)
    
    if not blob_conn_str or not blob_container:
        return JSONResponse(status_code=500, content={"error": "Falha de credenciais do Blob Storage."})

    # 1. Upload do Arquivo
    if arquivo_docx:
        async with BlobServiceClient.from_connection_string(blob_conn_str) as blob_service_client:
            container_client = blob_service_client.get_container_client(blob_container)
            
            if not await container_client.exists():
                await container_client.create_container()
                
            blob_name = f"{job_id}_{arquivo_docx.filename}"
            blob_client = container_client.get_blob_client(blob_name)
            
            conteudo = await arquivo_docx.read()
            await blob_client.upload_blob(conteudo, overwrite=True)
            blob_temp_path = f"{blob_container}/{blob_name}"

    # 2. Enviar para a Fila
    task_payload = {"job_id": job_id, "documento_blob_path": blob_temp_path} # Adicione os outros
    queue_conn_str = await vault_service.get_queue_connection_string()
    
    async with QueueClient.from_connection_string(conn_str=queue_conn_str, queue_name=settings.QUEUE_NAME) as queue_client:
        message_b64 = base64.b64encode(json.dumps(task_payload).encode('utf-8')).decode('utf-8')
        await queue_client.send_message(message_b64)

    return JSONResponse(status_code=202, content={"status": "queued", "job_id": job_id})
