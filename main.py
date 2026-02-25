import json
import asyncio
import logging
import logging.config
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import JSONResponse

# --- CONFIGURAÇÃO DE LOGGING ESTRUTURADO ---
class StructuredLogger(logging.Logger):
    def _log_struct(self, event, extra=None, level=logging.INFO, **kwargs):
        log_record = {
            "event": event,
            "level": logging.getLevelName(level),
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        }
        if extra:
            log_record.update(extra)
        self.log(level, json.dumps(log_record), **kwargs)

    def info_struct(self, event, extra=None):
        self._log_struct(event, extra=extra, level=logging.INFO)

    def error_struct(self, event, extra=None):
        self._log_struct(event, extra=extra, level=logging.ERROR)

    def debug_struct(self, event, extra=None):
        self._log_struct(event, extra=extra, level=logging.DEBUG)

# --- Definição do formato estruturado global ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": %(message)s}'

logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": LOG_FORMAT,
            "datefmt": "%Y-%m-%dT%H:%M:%S%z"
        }
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
            "stream": sys.stdout
        }
    },
    "root": {
        "handlers": ["stdout"],
        "level": LOG_LEVEL
    },
    "loggers": {
        "mcp_worker": {
            "handlers": ["stdout"],
            "level": LOG_LEVEL,
            "propagate": False
        },
        "uvicorn": {
            "handlers": ["stdout"],
            "level": LOG_LEVEL,
            "propagate": False
        }
    }
}
logging.config.dictConfig(logging_config)
logging.setLoggerClass(StructuredLogger)
logger = logging.getLogger("mcp_worker")

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
    logger.info_struct("worker_task_iniciado")
    worker_task = asyncio.create_task(queue_service.start_worker())
    yield
    logger.info_struct("worker_task_cancelando")
    worker_task.cancel()
    try:
        await worker_task
        logger.info_struct("worker_task_finalizado")
    except asyncio.CancelledError:
        logger.info_struct("worker_task_cancelled_success")

app = FastAPI(title="MCP Queue Worker", lifespan=lifespan)

# --- MIDDLEWARE DE LOG AUTOMÁTICO ---
@app.middleware("http")
async def log_request_middleware(request: Request, call_next):
    start_time = time.time()
    logger.info_struct(
        "http_request_iniciada",
        extra={
            "method": request.method,
            "path": request.url.path
        }
    )
    response = await call_next(request)
    process_time = round((time.time() - start_time) * 1000, 2)
    logger.info_struct(
        "http_request_finalizada",
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
    logger.info_struct(
        "api_request_recebido",
        extra={
            "job_id": job_id,
            "company_id": company_id,
            "analysis_type": analysis_type,
            "has_file": bool(arquivo_docx)
        }
    )
    nome_arquivo = None
    blob_path = None
    if arquivo_docx:
        nome_arquivo = arquivo_docx.filename
        logger.info_struct(
            "api_file_upload_iniciado",
            extra={"job_id": job_id, "filename": nome_arquivo}
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
            logger.info_struct(
                "api_file_upload_sucesso",
                extra={"job_id": job_id, "filename": nome_arquivo, "blob_path": blob_path}
            )
        except Exception as e:
            logger.error_struct(
                "api_file_upload_erro",
                extra={"job_id": job_id, "filename": nome_arquivo, "error": str(e)}
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
    logger.info_struct(
        "api_task_enfileirada",
        extra={"job_id": job_id, "company_id": company_id, "blob_path": blob_path}
    )
    try:
        await queue_service.send_message(task_payload)
    except Exception as e:
        logger.error_struct(
            "api_task_enfileirada_erro",
            extra={"job_id": job_id, "error": str(e)}
        )
        return JSONResponse(status_code=500, content={"error": "Falha ao enviar tarefa para a fila de processamento."})

    logger.info_struct(
        "api_request_finalizado",
        extra={"job_id": job_id, "status": "queued"}
    )
    return JSONResponse(
        status_code=202,
        content={
            "status": "queued",
            "job_id": job_id,
            "message": "Tarefa adicionada à fila de processamento."
        }
    )
