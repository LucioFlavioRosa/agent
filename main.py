import json
import asyncio
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import JSONResponse

from backend.app.utils.log_formatter import StructuredLogger

# Instanciamos o logger passando o nome do módulo
logger = StructuredLogger("mcp_worker")

# --- IMPORTAÇÃO DE CLASSES E CONFIGURAÇÕES ---
from backend.app.services.vault_service import VaultService
from backend.app.services.blob_storage_service import BlobStorageService
from backend.app.services.queue_service import QueueService
from backend.app.config.settings import settings

# --- INSTANCIAÇÃO DOS SERVIÇOS (ORQUESTRAÇÃO DAS DEPENDÊNCIAS) ---
vault_urls = [
    settings.AZURE_INFRA_VAULT_URL,
    settings.AZURE_LLM_VAULT_URL,
]
vault_service = VaultService(vault_urls=vault_urls)
blob_storage_service = BlobStorageService(vault_service=vault_service)
queue_service = QueueService(
    vault_service=vault_service,
    blob_storage_service=blob_storage_service,
    queue_name=settings.QUEUE_NAME
)

# --- LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Usando o método log_evento da sua classe oficial
    logger.log_evento("INFO", "worker_task_iniciado", "Iniciando worker em background")
    worker_task = asyncio.create_task(queue_service.start_worker())
    
    yield
    
    logger.log_evento("INFO", "worker_task_cancelando", "Sinal de parada recebido")
    worker_task.cancel()
    try:
        await worker_task
        logger.log_evento("INFO", "worker_task_finalizado", "Worker finalizado com sucesso")
    except asyncio.CancelledError:
        logger.log_evento("INFO", "worker_task_cancelled_success", "Worker cancelado com sucesso")

app = FastAPI(title="MCP Queue Worker", lifespan=lifespan)

# --- MIDDLEWARE DE LOG AUTOMÁTICO ---
@app.middleware("http")
async def log_request_middleware(request: Request, call_next):
    start_time = time.time()
    
    logger.log_evento(
        level="INFO",
        event="http_request_iniciada",
        mensagem=f"Recebendo requisição HTTP",
        extra={"method": request.method, "path": request.url.path}
    )
    
    response = await call_next(request)
    
    process_time = round((time.time() - start_time) * 1000, 2)
    logger.log_evento(
        level="INFO",
        event="http_request_finalizada",
        mensagem="Requisição HTTP concluída",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time_ms": process_time
        }
    )
    return response

# --- FUNÇÃO GERADORA DE STREAM ---
async def get_file_stream(upload_file: UploadFile, chunk_size: int = 4 * 1024 * 1024):
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
    # 🚀 ADIÇÃO: Imprimindo TODAS as variáveis recebidas no payload do Log
    logger.log_evento(
        level="INFO",
        event="api_request_recebido",
        mensagem="Requisição /start recebida",
        job_id=job_id,
        company_id=company_id,
        project_id=project_id,
        extra={
            "payload_recebido": {
                "group_ids": group_ids,
                "email": email,
                "nome_projeto": nome_projeto,
                "analysis_type": analysis_type,
                "branch": branch,
                "repository": repository,
                "comentario_extra": comentario_extra,
                "context_used": context_used,
                "has_file": bool(arquivo_docx),
                "filename": arquivo_docx.filename if arquivo_docx else None
            }
        }
    )
    logger.log_evento(
        level="INFO",
        event="api_request_recebido",
        mensagem="Requisição /start recebida",
        job_id=job_id,
        company_id=company_id,
        project_id=project_id,
        extra={"analysis_type": analysis_type, "has_file": bool(arquivo_docx)}
    )
    
    nome_arquivo = None
    blob_path = None
    
    if arquivo_docx:
        nome_arquivo = arquivo_docx.filename
        logger.log_evento(
            level="INFO",
            event="api_file_upload_iniciado",
            mensagem=f"Iniciando upload do arquivo {nome_arquivo}",
            job_id=job_id,
            company_id=company_id
        )
        try:
            file_stream = get_file_stream(arquivo_docx)
            blob_path = await blob_storage_service.save_document(
                company_id=company_id,
                project_id=project_id,
                job_id=job_id,
                file_data=file_stream,
                filename=nome_arquivo,
                group_id=group_ids
            )
            logger.log_evento(
                level="INFO",
                event="api_file_upload_sucesso",
                mensagem="Arquivo salvo no Blob Storage",
                job_id=job_id,
                company_id=company_id,
                extra={"blob_path": blob_path}
            )
        except Exception as e:
            logger.log_erro(
                event="api_file_upload_erro",
                mensagem=f"Erro ao salvar arquivo no Blob: {e}",
                job_id=job_id,
                company_id=company_id
            )
            return JSONResponse(status_code=500, content={"error": "Falha ao salvar arquivo no Blob Storage."})

    parsed_context = {}
    if context_used:
        try:
            parsed_context = json.loads(context_used)
        except Exception:
            parsed_context = {}

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
    
    logger.log_evento(
        level="INFO",
        event="api_task_enfileirada",
        mensagem="Enviando tarefa para a fila",
        job_id=job_id,
        company_id=company_id
    )
    
    try:
        await queue_service.send_message(task_payload)
    except Exception as e:
        logger.log_erro(
            event="api_task_enfileirada_erro",
            mensagem=f"Falha ao enviar para a fila: {e}",
            job_id=job_id,
            company_id=company_id
        )
        return JSONResponse(status_code=500, content={"error": "Falha ao enviar tarefa para a fila de processamento."})

    logger.log_evento(
        level="INFO",
        event="api_request_finalizado",
        mensagem="Tarefa adicionada à fila com sucesso",
        job_id=job_id,
        company_id=company_id
    )
    
    return JSONResponse(
        status_code=202,
        content={
            "status": "queued",
            "job_id": job_id,
            "message": "Tarefa adicionada à fila de processamento."
        }
    )
