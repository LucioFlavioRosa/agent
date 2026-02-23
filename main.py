import asyncio
import json
import base64
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import JSONResponse
from azure.storage.queue.aio import QueueClient

logger = logging.getLogger("mcp_worker")

# --- EXCEÇÕES DE BLOB ---
class BlobStorageConnectionError(Exception):
    pass

class BlobUploadError(Exception):
    pass

# --- SERVIÇO DE BLOB ---
class BlobStorageService:
    def __init__(self, vault_service):
        self.vault_service = vault_service

    async def upload_document(self, company_id: str, project_id: str, job_id: str, arquivo_docx: UploadFile) -> str:
        from azure.storage.blob.aio import BlobServiceClient
        import os
        try:
            # Busca a connection string específica para a company
            conn_str = await self.vault_service.get_secret('blobstorage-connection-string', company_id)
            if not conn_str:
                raise BlobStorageConnectionError(f"Connection string não encontrada para company_id {company_id}")
            container_name = company_id
            # Monta o caminho: company_id/project_id/job_id/nome_do_arquivo
            ext = os.path.splitext(arquivo_docx.filename)[1]
            blob_name = f"{company_id}/{project_id}/{job_id}/{arquivo_docx.filename}"
            async with BlobServiceClient.from_connection_string(conn_str) as blob_service_client:
                container_client = blob_service_client.get_container_client(container_name)
                if not await container_client.exists():
                    await container_client.create_container()
                blob_client = container_client.get_blob_client(blob_name)
                conteudo = await arquivo_docx.read()
                try:
                    await blob_client.upload_blob(conteudo, overwrite=True)
                except Exception as e:
                    raise BlobUploadError(f"Falha ao fazer upload do documento: {e}")
            return f"{container_name}/{project_id}/{job_id}/{arquivo_docx.filename}"
        except BlobStorageConnectionError as e:
            logger.error(f"❌ [BLOB] {e}")
            raise
        except BlobUploadError as e:
            logger.error(f"❌ [BLOB] {e}")
            raise
        except Exception as e:
            logger.error(f"❌ [BLOB] Erro inesperado: {e}")
            raise BlobUploadError(f"Erro inesperado: {e}")

# Instância global do VaultService
vault_urls = [
    settings.AZURE_INFRA_VAULT_URL,
    settings.AZURE_LLM_VAULT_URL,
    settings.AZURE_PROJECTS_VAULT_URL
]
vault_service = VaultService(vault_urls)

# Instância global do BlobStorageService
blob_storage_service = BlobStorageService(vault_service)

# --- WORKER ---
async def process_queue_messages():
    logger.info("👷 Worker iniciado...")
    
    queue_conn_str = await vault_service.get_queue_connection_string()
    if not queue_conn_str:
        logger.error("❌ Abortando worker: Sem connection string da fila.")
        return

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
    project_id: str = Form(...),
    company_id: str = Form(...),
    group_ids: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    nome_projeto: Optional[str] = Form(None),
    analysis_type: Optional[str] = Form(None),
    branch: Optional[str] = Form(None),
    repository: Optional[str] = Form(None),
    comentario_extra: Optional[str] = Form(None),
    arquivo_docx: Optional[UploadFile] = File(None)
):
    blob_temp_path = None
    
    # Busca credenciais do Azure Blob no Key Vault
    blob_conn_str = await vault_service.get_secret('blobstorage-connection-string', company_id, group_ids)
    blob_container = company_id
    
    if not blob_conn_str or not blob_container:
        return JSONResponse(status_code=500, content={"error": "Falha de credenciais do Blob Storage."})

    # 1. Upload do Arquivo
    if arquivo_docx:
        try:
            blob_temp_path = await blob_storage_service.upload_document(company_id, project_id, job_id, arquivo_docx)
        except BlobStorageConnectionError as e:
            return JSONResponse(status_code=500, content={"error": f"Erro de conexão com Blob Storage: {str(e)}"})
        except BlobUploadError as e:
            return JSONResponse(status_code=500, content={"error": f"Erro ao fazer upload do documento: {str(e)}"})

    # 2. Montar a "ficha" para a fila com todos os parâmetros
    task_payload = {
        "job_id": job_id,
        "project_id": project_id,
        "company_id": company_id,
        "group_ids": group_ids,
        "email": email,
        "nome_projeto": nome_projeto,
        "analysis_type": analysis_type,
        "branch": branch,
        "repository": repository,
        "comentario_extra": comentario_extra,
        "documento_blob_path": blob_temp_path
    }
    
    # 3. Enviar para a Fila do Azure
    queue_conn_str = await vault_service.get_queue_connection_string()
    
    if not queue_conn_str:
        return JSONResponse(status_code=500, content={"error": "Falha ao obter conexão da fila do Azure."})
    
    async with QueueClient.from_connection_string(conn_str=queue_conn_str, queue_name=settings.QUEUE_NAME) as queue_client:
        message_b64 = base64.b64encode(json.dumps(task_payload).encode('utf-8')).decode('utf-8')
        await queue_client.send_message(message_b64)

    # 4. Retornar status 202
    return JSONResponse(
        status_code=202, 
        content={
            "status": "queued", 
            "job_id": job_id,
            "message": "Tarefa adicionada à fila de processamento."
        }
    )
