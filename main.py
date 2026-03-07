import os
import re
import sys
import time
import json
import ast
import asyncio
import unicodedata

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import JSONResponse

from app.utils.log_formatter import StructuredLogger
from app.services.vault_service import VaultService
from app.services.blob_storage_service import BlobStorageService
from app.services.queue_service import QueueService
# from app.config.settings import settings  # Ajuste o import do settings conforme sua pasta

logger = StructuredLogger("mcp_prototype_worker")

# --- INSTANCIAÇÃO DOS SERVIÇOS ---
# Pegando das variáveis de ambiente ou do seu settings.py
vault_urls = [
    os.getenv("AZURE_INFRA_VAULT_URL", ""),
    os.getenv("AZURE_LLM_VAULT_URL", ""),
]
queue_name_prototype = os.getenv("QUEUE_NAME", "prototype-queue")

vault_service = VaultService(vault_urls=[u for u in vault_urls if u])
blob_storage_service = BlobStorageService() # Já usa o vault_service global internamente
queue_service = QueueService(
    queue_name=queue_name_prototype,
    max_concurrent_workers=5
)

def sanitize_filename(filename: str, fallback_name: str = "documento.docx") -> str:
    if not filename:
        return fallback_name
    nfkd_form = unicodedata.normalize('NFKD', filename)
    sem_acento = u"".join([c for c in nfkd_form if not unicodedata.combining(c)])
    limpo = re.sub(r'[^a-zA-Z0-9_.-]', '_', sem_acento)
    return re.sub(r'_+', '_', limpo).lower()

# --- LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.log_evento("INFO", "worker_task_iniciado", "Iniciando worker do Protótipo em background")
    worker_task = asyncio.create_task(queue_service.start_worker())
    yield
    logger.log_evento("INFO", "worker_task_cancelando", "Sinal de parada recebido")
    worker_task.cancel()
    try:
        await worker_task
        logger.log_evento("INFO", "worker_task_finalizado", "Worker finalizado com sucesso")
    except asyncio.CancelledError:
        logger.log_evento("INFO", "worker_task_cancelled_success", "Worker cancelado com sucesso")

app = FastAPI(title="MCP Prototype Queue Worker", lifespan=lifespan)
app.state.blob_storage_service = blob_storage_service

@app.middleware("http")
async def log_request_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = round((time.time() - start_time) * 1000, 2)
    logger.log_evento(
        level="INFO",
        event="http_request_finalizada",
        mensagem="Requisição HTTP concluída",
        extra={"method": request.method, "path": request.url.path, "status_code": response.status_code, "process_time_ms": process_time}
    )
    return response

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
    
    # 🚀 AQUI ESTÁ A GRANDE MUDANÇA: Aceita os DOIS arquivos do Frontend/Maestro
    arquivo_docx: Optional[UploadFile] = File(None),
    arquivo_identidade: Optional[UploadFile] = File(None)
):
    # =========================================================================
    # 🚀 PARSING BLINDADO DO CONTEXT_USED
    # Como o protótipo "começa do zero", ele vai processar graciosamente 
    # se o context_used vier vazio ({}) do Maestro.
    # =========================================================================
    parsed_context = {}
    if context_used and context_used.strip():
        clean_context_str = context_used.strip()
        try:
            json_friendly_str = clean_context_str.replace("'", '"')
            parsed_context = json.loads(json_friendly_str)
        except Exception:
            try:
                parsed_context = ast.literal_eval(clean_context_str)
                if not isinstance(parsed_context, dict): parsed_context = {}
            except Exception:
                parsed_context = {}

    parsed_group_id = None
    if group_ids:
        try:
            g_val = ast.literal_eval(group_ids)
            parsed_group_id = str(g_val[0]) if isinstance(g_val, list) and len(g_val) > 0 else str(group_ids)
        except:
            parsed_group_id = str(group_ids)

    # =========================================================================
    # 🚀 UPLOAD PARA O BLOB STORAGE (DOIS ARQUIVOS)
    # =========================================================================
    blob_path = None
    blob_identidade_path = None
    
    try:
        # 1. Salva o DOCX de Instruções (Se existir)
        if arquivo_docx:
            nome_arquivo = sanitize_filename(arquivo_docx.filename, "instrucoes.docx")
            file_bytes = await arquivo_docx.read()
            blob_path = await blob_storage_service.save_document(
                company_id=company_id, project_id=project_id, job_id=job_id,
                file_data=file_bytes, filename=nome_arquivo, group_id=parsed_group_id
            )

        # 2. Salva o DOCX de Identidade Visual (Se existir)
        if arquivo_identidade:
            nome_identidade = sanitize_filename(arquivo_identidade.filename, "identidade.docx")
            identidade_bytes = await arquivo_identidade.read()
            blob_identidade_path = await blob_storage_service.save_document(
                company_id=company_id, project_id=project_id, job_id=job_id,
                file_data=identidade_bytes, filename=nome_identidade, group_id=parsed_group_id
            )
            
    except Exception as e:
        logger.log_erro("erro_upload_blob", f"Falha ao salvar arquivos: {e}")
        return JSONResponse(status_code=500, content={"error": "Falha ao salvar arquivos base."})

    # =========================================================================
    # 🚀 MONTAGEM DO PAYLOAD DA FILA
    # =========================================================================
    task_payload = {
        "job_id": job_id,
        "project_id": project_id,
        "company_id": company_id,
        "group_ids": parsed_group_id,
        "email": email,
        "nome_projeto": nome_projeto,
        "analysis_type": analysis_type,
        "branch": branch,
        "repository": repository,
        "comentario_extra": comentario_extra,
        
        # Passa os dois caminhos do Blob Storage para o Queue Worker ler
        "blob_path": blob_path, 
        "identidade_visual_blob_path": blob_identidade_path, 
        
        "context_used": parsed_context,
    }
    
    try:
        await queue_service.send_message(task_payload)
        logger.log_evento("INFO", "task_enviada_fila", "Mensagem colocada na fila de prototipação com sucesso.")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "Falha ao enviar tarefa para a fila."})

    return JSONResponse(status_code=202, content={"status": "queued", "job_id": job_id})
