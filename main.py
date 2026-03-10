import os
import re
import sys
import ast
import time
import json
import asyncio
import traceback
import unicodedata

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import JSONResponse

from app.utils.log_formatter import StructuredLogger
from app.services.vault_service import VaultService
from app.services.blob_storage_service import BlobStorageService
from app.services.queue_service import QueueService

logger = StructuredLogger("mcp_prototype_worker")

# --- CONFIGURAÇÕES DE AMBIENTE ---
vault_urls = [
    os.getenv("AZURE_INFRA_VAULT_URL", ""),
    os.getenv("AZURE_LLM_VAULT_URL", ""),
]
queue_name_prototype = os.getenv("QUEUE_NAME", "prototype-queue")

# --- INICIALIZAÇÃO DOS SERVIÇOS (Injeção de Dependência) ---
# 1. Cofre é a base de tudo
vault_service = VaultService(vault_urls=[u for u in vault_urls if u])

# 2. Blob Storage recebe o cofre
blob_storage_service = BlobStorageService(vault_service=vault_service) 

# 3. Fila recebe o cofre e o blob (ela instanciará o Agente e o Context internamente)
queue_service = QueueService(
    vault_service=vault_service,
    blob_storage_service=blob_storage_service,
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

# --- LIFESPAN (Gerenciamento do Worker) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 [BOOT] Iniciando Worker de Prototipação...", flush=True)
    
    # 🛡️ Criamos um escudo para capturar qualquer erro fatal no background
    async def run_worker_safely():
        try:
            await queue_service.start_worker()
        except Exception as e:
            print(f"\n❌ [ERRO FATAL NO WORKER] A fila parou de rodar! Motivo: {str(e)}", flush=True)
            import traceback
            traceback.print_exc()

    # Inicia a tarefa com o escudo
    worker_task = asyncio.create_task(run_worker_safely())
    
    yield
    
    print("🛑 [SHUTDOWN] Cancelando worker...", flush=True)
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

app = FastAPI(title="MCP Prototype Queue Worker", lifespan=lifespan)

# Middleware para Logs de Requisição
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
    
    # Arquivos Multipart
    arquivo_docx: Optional[UploadFile] = File(None),
    arquivo_identidade: Optional[UploadFile] = File(None)
):
    # 1. Parsing do Contexto (Lógica Blindada)
    parsed_context = {}
    if context_used and context_used.strip():
        try:
            parsed_context = json.loads(context_used.replace("'", '"'))
        except:
            try:
                parsed_context = ast.literal_eval(context_used)
            except:
                parsed_context = {}

    # 2. Parsing do Group ID
    parsed_group_id = None
    if group_ids:
        try:
            g_val = ast.literal_eval(group_ids)
            parsed_group_id = str(g_val[0]) if isinstance(g_val, list) and len(g_val) > 0 else str(group_ids)
        except:
            parsed_group_id = str(group_ids)

    # 3. Upload dos arquivos para o Blob
    blob_path = None
    blob_identidade_path = None
    
    try:
        # Arquivo 1: Instruções
        if arquivo_docx and arquivo_docx.filename:
            nome_arquivo = sanitize_filename(arquivo_docx.filename, "instrucoes.docx")
            file_bytes = await arquivo_docx.read()
            blob_path = await blob_storage_service.save_document(
                company_id=company_id, project_id=project_id, job_id=job_id,
                file_data=file_bytes, filename=nome_arquivo, group_id=parsed_group_id
            )

        # Arquivo 2: Identidade Visual
        if arquivo_identidade and arquivo_identidade.filename:
            nome_identidade = sanitize_filename(arquivo_identidade.filename, "identidade.docx")
            identidade_bytes = await arquivo_identidade.read()
            blob_identidade_path = await blob_storage_service.save_document(
                company_id=company_id, project_id=project_id, job_id=job_id,
                file_data=identidade_bytes, filename=nome_identidade, group_id=parsed_group_id
            )
            
    except Exception as e:
        print(f"❌ [{job_id}] ERRO NO BLOB STORAGE: {str(e)}", flush=True)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": f"Falha no Blob: {str(e)}"})

    # 4. Envio para a Fila
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
        "blob_path": blob_path, 
        "identidade_visual_blob_path": blob_identidade_path, 
        "context_used": parsed_context,
    }
    
    try:
        await queue_service.send_message(task_payload)
        return JSONResponse(status_code=202, content={"status": "queued", "job_id": job_id})
    except Exception as e:
        print(f"❌ [{job_id}] ERRO AO ENVIAR PARA FILA: {str(e)}", flush=True)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": f"Falha na Fila: {str(e)}"})
