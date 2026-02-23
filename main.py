import logging
import json
import base64
import asyncio
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import JSONResponse

# Importação assíncrona do Azure
from azure.storage.queue.aio import QueueClient
from azure.storage.blob.aio import BlobServiceClient

# --- CONFIGURAÇÃO DE LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp_worker")

# --- CONFIGURAÇÕES DO AZURE ---
# Em produção, o Azure Key Vault injeta isso nas variáveis de ambiente
AZURE_STORAGE_CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "sua_connection_string_aqui")
QUEUE_NAME = "mcp-tasks-queue"
TEMP_BLOB_CONTAINER = "mcp-temp-docs" # Container para os arquivos .docx temporários

# ---------------------------------------------------------
# WORKER: O "Trabalhador" que lê da Fila em background
# ---------------------------------------------------------
async def process_queue_messages():
    """Fica rodando em loop puxando tarefas da fila e processando."""
    logger.info("👷 Worker iniciado e escutando a fila do Azure...")
    
    # Inicia o cliente da fila
    queue_client = QueueClient.from_connection_string(conn_str=AZURE_STORAGE_CONN_STR, queue_name=QUEUE_NAME)
    
    try:
        await queue_client.create_queue()
    except Exception:
        pass # Ignora se a fila já existir

    async with queue_client:
        while True:
            try:
                # Puxa até 5 mensagens, invisíveis para outros por 5 minutos (300s)
                messages = queue_client.receive_messages(max_messages=5, visibility_timeout=300)
                
                async for msg in messages:
                    # 1. Decodifica a mensagem Base64 -> JSON
                    decoded_str = base64.b64decode(msg.content).decode('utf-8')
                    task_data = json.loads(decoded_str)
                    
                    job_id = task_data.get('job_id')
                    project_id = task_data.get('project_id')
                    analysis_type = task_data.get('analysis_type')
                    
                    logger.info(f"🔥 [WORKER] Pegou a tarefa! Iniciando job: {job_id} | Agente: {analysis_type}")
                    
                    # ==========================================
                    # 2. AQUI ENTRA A SUA LÓGICA DE IA
                    # Você tem acesso a todos os parâmetros aqui:
                    # task_data.get('comentario_extra')
                    # task_data.get('email')
                    # task_data.get('documento_blob_path') -> Caminho para baixar o .docx se precisar
                    # ==========================================
                    
                    await asyncio.sleep(5) # Simulando o processamento demorado da IA...
                    
                    # 3. SALVARIA O MARKDOWN FINAL NO BLOB
                    logger.info(f"✅ [WORKER] IA finalizou o job {job_id}.")
                    
                    # 4. CHAMARIA O WEBHOOK DO BACKEND
                    # payload = {"project_id": project_id, "company_id": task_data.get("company_id"), "status": "done", "category": "...", "blob_path": "..."}
                    # requests.post(webhook_url, json=payload)
                    logger.info(f"🔔 [WORKER] Webhook disparado para o backend (job: {job_id}).")
                    
                    # 5. Apaga a mensagem da fila (sucesso)
                    await queue_client.delete_message(msg)
                    logger.info(f"🗑️ [WORKER] Mensagem do job {job_id} apagada da fila com sucesso.")

            except Exception as e:
                logger.error(f"Erro no loop do worker da fila: {e}")
                
            await asyncio.sleep(3)

# --- LIFESPAN DO FASTAPI ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_task = asyncio.create_task(process_queue_messages())
    yield
    worker_task.cancel()

app = FastAPI(
    title="MCP - Azure Queue Worker", 
    description="Microserviço de IA com processamento assíncrono via fila.",
    version="1.0.0",
    lifespan=lifespan
)

# ---------------------------------------------------------
# RECEPCIONISTA: Rota que recebe os dados do Backend
# ---------------------------------------------------------
@app.post("/api/v1/analysis/start", tags=["Analysis"])
@app.post("/start", tags=["Analysis"])
async def start_analysis(
    request: Request,
    project_id: str = Form(...),
    job_id: str = Form(...),
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
    logger.info(f"📥 [RECEPCIONISTA] Requisição recebida do backend para o job: {job_id}")

    blob_temp_path = None

    # 1. TRATAR O ARQUIVO (Upload pro Azure Blob Storage)
    if arquivo_docx:
        try:
            blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONN_STR)
            container_client = blob_service_client.get_container_client(TEMP_BLOB_CONTAINER)
            
            # Cria o container de temporários se não existir
            if not await container_client.exists():
                await container_client.create_container()

            # Salva no blob com um nome único: jobid_nomearquivo.docx
            blob_name = f"{job_id}_{arquivo_docx.filename}"
            blob_client = container_client.get_blob_client(blob_name)
            
            # Lê os bytes e faz o upload
            conteudo = await arquivo_docx.read()
            await blob_client.upload_blob(conteudo, overwrite=True)
            
            blob_temp_path = f"{TEMP_BLOB_CONTAINER}/{blob_name}"
            logger.info(f"☁️ [RECEPCIONISTA] Arquivo salvo no Blob em: {blob_temp_path}")
            
        except Exception as e:
            logger.error(f"Erro ao salvar arquivo no Blob Storage: {e}")
            # Você pode decidir se quer travar a requisição aqui ou continuar sem o arquivo
            return JSONResponse(status_code=500, content={"error": f"Erro ao salvar arquivo no storage: {str(e)}"})

    # 2. MONTAR A "FICHA" PARA A FILA COM TODOS OS PARÂMETROS
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
        "documento_blob_path": blob_temp_path # A IA vai usar isso para baixar o arquivo depois
    }

    # 3. ENVIAR PARA A FILA DO AZURE
    try:
        queue_client = QueueClient.from_connection_string(conn_str=AZURE_STORAGE_CONN_STR, queue_name=QUEUE_NAME)
        
        # Converte o dicionário para JSON String e depois para Base64 (Exigência do Azure)
        message_str = json.dumps(task_payload)
        message_b64 = base64.b64encode(message_str.encode('utf-8')).decode('utf-8')
        
        async with queue_client:
            await queue_client.send_message(message_b64)
            
        logger.info(f"🎟️ [RECEPCIONISTA] Ficha do job {job_id} enviada para a Fila do Azure com todos os parâmetros!")
        
    except Exception as e:
        logger.error(f"Erro ao colocar na fila: {e}")
        return JSONResponse(status_code=500, content={"error": "Falha ao enfileirar tarefa de análise."})

    # 4. DEVOLVER A RESPOSTA RAPIDAMENTE (202 Accepted)
    return JSONResponse(
        status_code=202,
        content={
            "message": "Tarefa adicionada à fila de processamento.",
            "job_id": job_id,
            "status": "queued"
        }
    )

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "message": "MCP Queue Worker is running"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
