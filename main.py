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

from backend.app.config.settings import settings

logger = logging.getLogger("mcp_worker")

# --- Helper para geração de caminhos e upload de arquivos ---
ANALYSIS_TYPE_MAPPING = {
    "agent_epics_generator_digital": "epics",
    "agent_epics_reviwer_digital": "epics",
    "agent_features_generator_digital": "features",
    "agent_featuares_reviwer_digital": "features",
    "agent_timeline_generator_digital": "timeline",
    "agent_timeline_reviwer_digital": "timeline",
    "agent_risks_generator_digital": "risks",
    "agent_risks_reviwer_digital": "risks"
}

def generate_blob_path(company_id: str, email: str, project_id: str, job_id: str, report_type: str, filename: str) -> str:
    return f"{company_id}/{email}/{project_id}/{job_id}/{report_type}.{filename}"

async def upload_file_to_blob(blob_conn_str: str, blob_container: str, blob_path: str, content: bytes):
    async with BlobServiceClient.from_connection_string(blob_conn_str) as blob_service_client:
        container_client = blob_service_client.get_container_client(blob_container)
        if not await container_client.exists():
            await container_client.create_container()
        blob_client = container_client.get_blob_client(blob_path)
        await blob_client.upload_blob(content, overwrite=True)

async def save_markdown_report(blob_conn_str: str, blob_container: str, blob_path: str, report_content: str):
    await upload_file_to_blob(blob_conn_str, blob_container, blob_path, report_content.encode("utf-8"))

class DocumentStorageService:
    @staticmethod
    async def save_analysis_report(company_id: str, email: str, project_id: str, job_id: str, analysis_type: str, report_content: str, blob_conn_str: str, blob_container: str):
        report_type = ANALYSIS_TYPE_MAPPING.get(analysis_type, "report")
        blob_path = f"{company_id}/{email}/{project_id}/{job_id}/{report_type}.md"
        await save_markdown_report(blob_conn_str, blob_container, blob_path, report_content)

# Instância global do VaultService
from backend.app.services.vault_service import VaultService
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
                    
                    # --- Salvar relatório gerado pela IA ---
                    company_id = task_data.get('company_id')
                    email = task_data.get('email') or "unknown"
                    project_id = task_data.get('project_id') or "unknown"
                    job_id = task_data.get('job_id') or "unknown"
                    analysis_type = task_data.get('analysis_type') or "unknown"
                    group_ids = task_data.get('group_ids')

                    # Buscar credenciais do Blob
                    blob_conn_str = await vault_service.get_secret('blobstorage-connection-string', company_id, group_ids)
                    blob_container = await vault_service.get_secret('blobstorage-container-name', company_id, group_ids)
                    if not blob_container:
                        blob_container = settings.DEFAULT_BLOB_CONTAINER
                    if not blob_conn_str:
                        logger.error("❌ Falha de credenciais do Blob Storage. Relatório não será salvo.")
                    else:
                        report_content = "# Relatório de Análise\n\nConteúdo gerado pela IA..."
                        try:
                            await DocumentStorageService.save_analysis_report(
                                company_id=company_id,
                                email=email,
                                project_id=project_id,
                                job_id=job_id,
                                analysis_type=analysis_type,
                                report_content=report_content,
                                blob_conn_str=blob_conn_str,
                                blob_container=blob_container
                            )
                            logger.info(f"📄 Relatório salvo em Blob Storage para job {job_id}.")
                        except Exception as e:
                            logger.error(f"❌ Erro ao salvar relatório no Blob Storage: {e}")
                    
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
    blob_container = await vault_service.get_secret('blobstorage-container-name', company_id, group_ids)
    if not blob_container:
        blob_container = settings.DEFAULT_BLOB_CONTAINER
    
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
