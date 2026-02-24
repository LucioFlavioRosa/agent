import json
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import JSONResponse

# --- IMPORTAÇÃO DE CLASSES E CONFIGURAÇÕES ---
from backend.app.services.vault_service import VaultService
from backend.app.services.blob_storage_service import BlobStorageService
from backend.app.services.queue_service import QueueService
from backend.app.config.settings import settings

logger = logging.getLogger("mcp_worker")

# --- INSTANCIAÇÃO DOS SERVIÇOS (ORQUESTRAÇÃO DAS DEPENDÊNCIAS) ---
# 1. Montamos as URLs dos cofres a partir do settings
vault_urls = [
    settings.AZURE_INFRA_VAULT_URL,
    settings.AZURE_LLM_VAULT_URL,
    #settings.AZURE_PROJECTS_VAULT_URL
]

# 2. Instanciamos o Vault
vault_service = VaultService(vault_urls=vault_urls)

# 3. MUDANÇA: Passamos o vault para o Blob Storage
blob_storage_service = BlobStorageService(vault_service=vault_service)

# 4. MUDANÇA: Passamos o vault e o blob_storage para a Fila
queue_service = QueueService(
    vault_service=vault_service,
    blob_storage_service=blob_storage_service,
    queue_name=settings.QUEUE_NAME
)


# --- LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_task = asyncio.create_task(queue_service.start_worker())
    yield
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        logger.info("👷 Worker parado com sucesso.")

app = FastAPI(title="MCP Queue Worker", lifespan=lifespan)

# --- FUNÇÃO GERADORA DE STREAM ---
async def get_file_stream(upload_file: UploadFile, chunk_size: int = 4 * 1024 * 1024):
    """
    Lê o arquivo recebido em pedaços (chunks) de 4MB, 
    evitando que arquivos grandes estourem a memória RAM.
    """
    while True:
        chunk = await upload_file.read(chunk_size)
        if not chunk:
            break
        yield chunk

# --- ENDPOINTS ---
@app.post("/start")
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
    context_used: Optional[str] = Form(None),
    arquivo_docx: Optional[UploadFile] = File(None)
):
    nome_arquivo = None
    blob_path = None # MUDANÇA: Variável para guardar o caminho retornado
    
    if arquivo_docx:
        nome_arquivo = arquivo_docx.filename
        
        # Passamos a função geradora no lugar do conteúdo inteiro lido na RAM
        file_stream = get_file_stream(arquivo_docx)
        
        # MUDANÇA: Capturamos o retorno nesta variável
        blob_path = await blob_storage_service.save_document(
            company_id=company_id,
            project_id=project_id,
            job_id=job_id,
            file_data=file_stream, 
            filename=nome_arquivo,
            group_id=group_ids
        )

    parsed_context = {}
    if context_used:
        try:
            parsed_context = json.loads(context_used)
        except Exception as e:
            logger.error(f"Erro ao fazer parse do context_used: {e}")

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
        "nome_arquivo_recebido": nome_arquivo,
        "blob_path": blob_path,
        "context_used": parsed_context,
    }

    try:
        await queue_service.send_message(task_payload)
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem para a fila: {e}")
        return JSONResponse(status_code=500, content={"error": "Falha ao enviar tarefa para a fila de processamento."})

    return JSONResponse(
        status_code=202,
        content={
            "status": "queued",
            "job_id": job_id,
            "message": "Tarefa adicionada à fila de processamento."
        }
    )
