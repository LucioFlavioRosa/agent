import logging
import json
import base64
import asyncio
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Form, UploadFile, File, Request, BackgroundTasks
from fastapi.responses import JSONResponse

# Importação assíncrona do Azure
from azure.storage.queue.aio import QueueClient

# --- CONFIGURAÇÃO DE LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp_worker")

# --- CONFIGURAÇÕES DO AZURE ---
AZURE_STORAGE_CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "sua_connection_string_aqui")
QUEUE_NAME = "mcp-tasks-queue"

# ---------------------------------------------------------
# WORKER: O "Trabalhador" que lê da Fila em background
# ---------------------------------------------------------
async def process_queue_messages():
    """Fica rodando em loop infinito puxando tarefas da fila e processando."""
    logger.info("👷 Worker iniciado e escutando a fila do Azure...")
    
    # Inicia o cliente da fila
    queue_client = QueueClient.from_connection_string(conn_str=AZURE_STORAGE_CONN_STR, queue_name=QUEUE_NAME)
    
    # Cria a fila se ela não existir
    try:
        await queue_client.create_queue()
    except Exception:
        pass # Fila já existe

    async with queue_client:
        while True:
            try:
                # Puxa até 5 mensagens por vez, escondendo-as de outros workers por 5 minutos (300 seg)
                # O tempo de invisibilidade deve ser maior que o tempo máximo que a IA demora para responder
                messages = queue_client.receive_messages(max_messages=5, visibility_timeout=300)
                
                async for msg in messages:
                    # 1. Decodifica a mensagem (O Azure usa Base64 por padrão)
                    decoded_str = base64.b64decode(msg.content).decode('utf-8')
                    task_data = json.loads(decoded_str)
                    
                    job_id = task_data.get('job_id')
                    logger.info(f"🔥 [WORKER] Pegou a tarefa na fila! Iniciando processamento do job: {job_id}")
                    
                    # ==========================================
                    # 2. AQUI ENTRA A SUA LÓGICA DE IA (OPENAI, ETC)
                    # ==========================================
                    await asyncio.sleep(5) # Simulando o tempo de processamento da IA...
                    
                    # 3. SALVARIA NO BLOB STORAGE AQUI
                    logger.info(f"✅ [WORKER] IA finalizou! Arquivo markdown gerado e salvo no Blob para o job: {job_id}.")
                    
                    # 4. CHAMARIA O WEBHOOK DO BACKEND AQUI
                    # requests.post(webhook_url, json={...})
                    logger.info(f"🔔 [WORKER] Webhook disparado para o backend (job: {job_id}).")
                    
                    # ==========================================
                    
                    # 5. Missão cumprida: Deleta a mensagem da fila para não ser processada de novo
                    await queue_client.delete_message(msg)
                    logger.info(f"🗑️ [WORKER] Mensagem do job {job_id} apagada da fila com sucesso.")

            except Exception as e:
                logger.error(f"Erro no loop do worker da fila: {e}")
                
            # Espera 3 segundos antes de checar a fila novamente se ela estiver vazia
            await asyncio.sleep(3)


# --- LIFESPAN DO FASTAPI ---
# Isso garante que o worker inicie junto com o servidor e morra quando o servidor parar
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Liga o Worker no background
    worker_task = asyncio.create_task(process_queue_messages())
    yield
    # Desliga o Worker suavemente
    worker_task.cancel()

app = FastAPI(title="MCP - Azure Queue Worker", lifespan=lifespan)


# ---------------------------------------------------------
# RECEPCIONISTA: A Rota que recebe os dados do Backend
# ---------------------------------------------------------
@app.post("/api/v1/analysis/start", tags=["Analysis"])
@app.post("/start", tags=["Analysis"])
async def start_analysis(
    project_id: str = Form(...),
    job_id: str = Form(...),
    company_id: str = Form(...),
    analysis_type: Optional[str] = Form(None),
    arquivo_docx: Optional[UploadFile] = File(None)
    # ... outros campos
):
    logger.info(f"📥 [RECEPCIONISTA] Requisição recebida do backend para o job: {job_id}")

    # 1. TRATAR O ARQUIVO ANTES DE IR PRA FILA
    blob_temp_path = None
    if arquivo_docx:
        # AQUI VOCÊ DEVE SALVAR O ARQUIVO NO BLOB STORAGE E GUARDAR O CAMINHO
        blob_temp_path = f"temp_docs/{job_id}_{arquivo_docx.filename}"
        logger.info(f"☁️ [RECEPCIONISTA] Arquivo salvo temporariamente no Blob em: {blob_temp_path}")

    # 2. MONTAR A "FICHA" PARA A FILA (O Payload)
    task_payload = {
        "job_id": job_id,
        "project_id": project_id,
        "company_id": company_id,
        "analysis_type": analysis_type,
        "documento_blob_path": blob_temp_path
    }

    # 3. ENVIAR PARA A FILA DO AZURE
    try:
        queue_client = QueueClient.from_connection_string(conn_str=AZURE_STORAGE_CONN_STR, queue_name=QUEUE_NAME)
        
        # O Azure Queue exige (ou recomenda fortemente) que strings sejam Base64 encoded
        message_str = json.dumps(task_payload)
        message_b64 = base64.b64encode(message_str.encode('utf-8')).decode('utf-8')
        
        async with queue_client:
            await queue_client.send_message(message_b64)
            
        logger.info(f"🎟️ [RECEPCIONISTA] Ficha do job {job_id} enviada para a Fila do Azure!")
        
    except Exception as e:
        logger.error(f"Erro ao colocar na fila: {e}")
        # Retorne 500 para o backend saber que falhou e marcar como erro no Redis dele
        return JSONResponse(status_code=500, content={"error": "Falha ao enfileirar tarefa."})

    # 4. DEVOLVE A RESPOSTA RAPIDINHO
    return JSONResponse(
        status_code=202,
        content={
            "message": "Tarefa adicionada à fila de processamento.",
            "job_id": job_id,
            "status": "queued"
        }
    )
