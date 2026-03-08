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

from backend.app.utils.log_formatter import StructuredLogger
from backend.app.services.vault_service import VaultService, vault_service
from backend.app.services.blob_storage_service import BlobStorageService
from backend.app.services.queue_service import QueueService
from backend.app.config.settings import settings
from backend.app.api.reports import router as reports_router

logger = StructuredLogger("mcp_worker")

# --- INSTANCIAÇÃO DOS SERVIÇOS ---
blob_storage_service = BlobStorageService(vault_service=vault_service)
queue_service = QueueService(
    vault_service=vault_service,
    blob_storage_service=blob_storage_service,
    queue_name=settings.QUEUE_NAME
)
def sanitize_filename(filename: str) -> str:
    if not filename:
        return "documento_base.docx"
    nfkd_form = unicodedata.normalize('NFKD', filename)
    sem_acento = u"".join([c for c in nfkd_form if not unicodedata.combining(c)])
    limpo = re.sub(r'[^a-zA-Z0-9_.-]', '_', sem_acento)
    return re.sub(r'_+', '_', limpo).lower()

# --- LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
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

app.state.blob_storage_service = blob_storage_service
app.include_router(reports_router, prefix="/reports", tags=["Reports"])

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
    arquivo_docx: Optional[UploadFile] = File(None)
):
    # =========================================================================
    # 🚀 PARSING BLINDADO DO CONTEXT_USED (O coração do problema)
    # =========================================================================
    parsed_context = {}
    print(f"\n[{job_id}] 📥 RAW CONTEXT RECEBIDO DO FASTAPI: {repr(context_used)}", flush=True)

    if context_used and context_used.strip():
        # Limpa espaços e formatações estranhas
        clean_context_str = context_used.strip()
        
        # 1ª Tentativa: JSON padrão (aspas duplas)
        try:
            # Substitui aspas simples por aspas duplas como fallback rápido
            json_friendly_str = clean_context_str.replace("'", '"')
            parsed_context = json.loads(json_friendly_str)
            print(f"[{job_id}] ✅ CONTEXTO LIDO COMO JSON: {parsed_context}", flush=True)
        except Exception as e_json:
            # 2ª Tentativa: Avaliação de Dicionário Python Literal (ast)
            try:
                parsed_context = ast.literal_eval(clean_context_str)
                if not isinstance(parsed_context, dict):
                    parsed_context = {}
                print(f"[{job_id}] ✅ CONTEXTO LIDO COMO AST LITERAL: {parsed_context}", flush=True)
            except Exception as e_ast:
                print(f"[{job_id}] ❌ ERRO ABSOLUTO AO LER CONTEXTO. String inválida! JSON Error: {e_json} | AST Error: {e_ast}", flush=True)
                parsed_context = {}
    else:
        print(f"[{job_id}] ⚠️ NENHUM CONTEXTO FOI ENVIADO NA REQUISIÇÃO.", flush=True)

    # -------------------------------------------------------------------------
    
    parsed_group_id = None
    if group_ids:
        try:
            g_val = ast.literal_eval(group_ids)
            if isinstance(g_val, list) and len(g_val) > 0:
                parsed_group_id = str(g_val[0])
            else:
                parsed_group_id = str(group_ids)
        except:
            parsed_group_id = str(group_ids)

    nome_arquivo = None
    blob_path = None
    
    if arquivo_docx:
        nome_arquivo = sanitize_filename(arquivo_docx.filename)
        try:
            file_bytes = await arquivo_docx.read()
            blob_path = await blob_storage_service.save_document(
                company_id=company_id,
                project_id=project_id,
                job_id=job_id,
                file_data=file_bytes,
                filename=nome_arquivo,
                group_id=group_ids
            )
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": "Falha ao salvar arquivo."})

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
        "nome_arquivo_recebido": nome_arquivo,
        "blob_path": blob_path,
        "context_used": parsed_context,
    }
    
    try:
        await queue_service.send_message(task_payload)
    except Exception as e:
        # =================================================================
        # 🚀 ESTA É A MÁGICA: VAI IMPRIMIR O ERRO REAL NO LOG DA AZURE!
        # =================================================================
        import traceback
        print(f"❌ [{job_id}] ERRO FATAL NA FILA: {str(e)}", flush=True)
        traceback.print_exc() 
        return JSONResponse(status_code=500, content={"error": f"Falha na Fila: {str(e)}"})

    return JSONResponse(status_code=202, content={"status": "queued", "job_id": job_id})
