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

# --- SERVIÇO DE COFRE DE SEGREDOS ---
from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient

class VaultService:
    def __init__(self, vault_urls):
        self.vault_urls = vault_urls
        self.credential = DefaultAzureCredential()
        self.clients = {url: SecretClient(vault_url=url, credential=self.credential) for url in vault_urls}

    async def get_secret(self, base_name, company_id, group_ids):
        # Tenta buscar com company_id e group_ids
        secret_name = f"{base_name}-{company_id}-{group_ids}" if group_ids else f"{base_name}-{company_id}"
        for url in self.vault_urls:
            client = self.clients[url]
            try:
                secret = await client.get_secret(secret_name)
                logger.info(f"🔑 [VAULT] Segredo encontrado: {secret_name} em {url}")
                return secret.value
            except Exception:
                logger.info(f"🔑 [VAULT] Segredo não encontrado: {secret_name} em {url}")
                continue
        # Tenta buscar apenas com company_id
        if group_ids:
            fallback_secret_name = f"{base_name}-{company_id}"
            for url in self.vault_urls:
                client = self.clients[url]
                try:
                    secret = await client.get_secret(fallback_secret_name)
                    logger.info(f"🔑 [VAULT] Segredo fallback encontrado: {fallback_secret_name} em {url}")
                    return secret.value
                except Exception:
                    logger.info(f"🔑 [VAULT] Segredo fallback não encontrado: {fallback_secret_name} em {url}")
                    continue
        logger.error(f"❌ [VAULT] Nenhum segredo encontrado para {base_name} com company_id={company_id} group_ids={group_ids}")
        return None

    async def get_queue_connection_string(self):
        # A conexão da fila é fixa, busca apenas pelo nome padrão no primeiro cofre
        secret_name = "queue-connection-string"
        url = self.vault_urls[0]
        client = self.clients[url]
        try:
            secret = await client.get_secret(secret_name)
            logger.info(f"🔑 [VAULT] Segredo da fila encontrado: {secret_name} em {url}")
            return secret.value
        except Exception as e:
            logger.error(f"❌ [VAULT] Falha ao buscar segredo da fila: {secret_name} em {url} - {e}")
            return None

# --- CONFIGURAÇÕES DOS COFRES ---
# URLs dos cofres (exemplo, substitua pelos reais ou injete via env)
VAULT_URLS = [
    os.getenv("AZURE_INFRA_VAULT_URL", "https://infra-vault.vault.azure.net/"),
    os.getenv("AZURE_LLM_VAULT_URL", "https://llm-vault.vault.azure.net/"),
    os.getenv("AZURE_PROJECTS_VAULT_URL", "https://projects-vault.vault.azure.net/")
]
QUEUE_NAME = "mcp-tasks-queue"

# ---------------------------------------------------------
# WORKER: O "Trabalhador" que lê da Fila em background
# ---------------------------------------------------------
async def process_queue_messages():
    """Fica rodando em loop puxando tarefas da fila e processando."""
    logger.info("👷 Worker iniciado e escutando a fila do Azure...")
    
    vault_service = VaultService(VAULT_URLS)
    queue_conn_str = await vault_service.get_queue_connection_string()
    if not queue_conn_str:
        logger.error("❌ [WORKER] Não foi possível obter a conexão da fila do Vault.")
        return

    queue_client = QueueClient.from_connection_string(conn_str=queue_conn_str, queue_name=QUEUE_NAME)
    
    try:
        await queue_client.create_queue()
    except Exception:
        pass # Ignora se a fila já existir

    async with queue_client:
        while True:
            try:
                messages = queue_client.receive_messages(max_messages=5, visibility_timeout=300)
                async for msg in messages:
                    decoded_str = base64.b64decode(msg.content).decode('utf-8')
                    task_data = json.loads(decoded_str)
                    job_id = task_data.get('job_id')
                    project_id = task_data.get('project_id')
                    analysis_type = task_data.get('analysis_type')
                    logger.info(f"🔥 [WORKER] Pegou a tarefa! Iniciando job: {job_id} | Agente: {analysis_type}")
                    await asyncio.sleep(5) # Simulando o processamento demorado da IA...
                    logger.info(f"✅ [WORKER] IA finalizou o job {job_id}.")
                    logger.info(f"🔔 [WORKER] Webhook disparado para o backend (job: {job_id}).")
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
    vault_service = VaultService(VAULT_URLS)
    blob_conn_str = await vault_service.get_secret('blobstorage-connection-string', company_id, group_ids)
    blob_container = await vault_service.get_secret('blobstorage-container-name', company_id, group_ids)
    if not blob_conn_str or not blob_container:
        logger.error("❌ [RECEPCIONISTA] Não foi possível obter credenciais do Blob Storage do Vault.")
        return JSONResponse(status_code=500, content={"error": "Falha ao obter credenciais do Blob Storage."})
    # 1. TRATAR O ARQUIVO (Upload pro Azure Blob Storage)
    if arquivo_docx:
        try:
            blob_service_client = BlobServiceClient.from_connection_string(blob_conn_str)
            container_client = blob_service_client.get_container_client(blob_container)
            if not await container_client.exists():
                await container_client.create_container()
            blob_name = f"{job_id}_{arquivo_docx.filename}"
            blob_client = container_client.get_blob_client(blob_name)
            conteudo = await arquivo_docx.read()
            await blob_client.upload_blob(conteudo, overwrite=True)
            blob_temp_path = f"{blob_container}/{blob_name}"
            logger.info(f"☁️ [RECEPCIONISTA] Arquivo salvo no Blob em: {blob_temp_path}")
        except Exception as e:
            logger.error(f"Erro ao salvar arquivo no Blob Storage: {e}")
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
        "documento_blob_path": blob_temp_path
    }
    # 3. ENVIAR PARA A FILA DO AZURE
    try:
        queue_conn_str = await vault_service.get_queue_connection_string()
        if not queue_conn_str:
            logger.error("❌ [RECEPCIONISTA] Não foi possível obter conexão da fila do Vault.")
            return JSONResponse(status_code=500, content={"error": "Falha ao obter conexão da fila."})
        queue_client = QueueClient.from_connection_string(conn_str=queue_conn_str, queue_name=QUEUE_NAME)
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
