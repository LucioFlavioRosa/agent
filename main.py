import logging
import json
import base64
import asyncio
import os
from contextlib import asynccontextmanager
from typing import Optional, Any

from fastapi import FastAPI, Form, UploadFile, File, Request, Depends
from fastapi.responses import JSONResponse

# Importação assíncrona do Azure
from azure.storage.queue.aio import QueueClient
from azure.storage.blob.aio import BlobServiceClient

from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient

# --- CONFIGURAÇÃO DE LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp_worker")

# --- CONFIGURAÇÕES DE COFRES ---
# URLs dos cofres (apenas essas variáveis)
AZURE_INFRA_VAULT_URL = os.getenv("AZURE_INFRA_VAULT_URL", "https://cofre-infra.vault.azure.net/")
LLM_VAULT_URL = os.getenv("LLM_VAULT_URL", "https://cofre-llm.vault.azure.net/")
ORG_VAULT_URL = os.getenv("ORG_VAULT_URL", "https://cofre-org.vault.azure.net/")

TEMP_BLOB_CONTAINER = "mcp-temp-docs" # Container para os arquivos .docx temporários
QUEUE_NAME = "mcp-tasks-queue"

class SecretsManager:
    def __init__(self, infra_vault_url: str, llm_vault_url: str, org_vault_url: str):
        self.infra_vault_url = infra_vault_url
        self.llm_vault_url = llm_vault_url
        self.org_vault_url = org_vault_url
        self.credential = DefaultAzureCredential()
        self.infra_client = SecretClient(vault_url=self.infra_vault_url, credential=self.credential)
        self.llm_client = SecretClient(vault_url=self.llm_vault_url, credential=self.credential)
        self.org_client = SecretClient(vault_url=self.org_vault_url, credential=self.credential)

    async def get_blob_storage_credentials(self, company_id: str, group_id: Optional[str]) -> dict:
        # Busca nome e string de conexão
        keys = [
            (f"blobstorage-conection-string-{company_id}-{group_id}", f"blobstorage-contanier-name-{company_id}-{group_id}")
        ]
        if not group_id:
            keys.append((f"blobstorage-conection-string-{company_id}", f"blobstorage-contanier-name-{company_id}"))
        else:
            keys.append((f"blobstorage-conection-string-{company_id}", f"blobstorage-contanier-name-{company_id}"))

        for conn_key, cont_key in keys:
            try:
                conn_secret = await self.infra_client.get_secret(conn_key)
                cont_secret = await self.infra_client.get_secret(cont_key)
                return {
                    "connection_string": conn_secret.value,
                    "container_name": cont_secret.value
                }
            except Exception:
                continue
        raise Exception(f"Credenciais de Blob Storage não encontradas para company_id={company_id} group_id={group_id}")

    async def get_openai_api_key(self, company_id: str, group_id: Optional[str]) -> str:
        keys = [
            f"openai-api-key-{company_id}-{group_id}"
        ]
        if not group_id:
            keys.append(f"openai-api-key-{company_id}")
        else:
            keys.append(f"openai-api-key-{company_id}")
        for key in keys:
            try:
                secret = await self.llm_client.get_secret(key)
                return secret.value
            except Exception:
                continue
        raise Exception(f"OpenAI API Key não encontrada para company_id={company_id} group_id={group_id}")

    # Métodos para outros cofres podem ser adicionados aqui

# Instância global para o lifespan
secrets_manager: Optional[SecretsManager] = None

# --- LIFESPAN DO FASTAPI ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global secrets_manager
    logger.info("🔐 Inicializando SecretsManager e conexões com Key Vaults...")
    secrets_manager = SecretsManager(
        infra_vault_url=AZURE_INFRA_VAULT_URL,
        llm_vault_url=LLM_VAULT_URL,
        org_vault_url=ORG_VAULT_URL
    )
    # Testa conexão inicial (opcional)
    try:
        await secrets_manager.infra_client.get_secret("test")
    except Exception:
        pass
    worker_task = asyncio.create_task(process_queue_messages(secrets_manager))
    yield
    worker_task.cancel()

app = FastAPI(
    title="MCP - Azure Queue Worker", 
    description="Microserviço de IA com processamento assíncrono via fila.",
    version="1.0.0",
    lifespan=lifespan
)

# Dependency para injetar o SecretsManager
async def get_secrets_manager() -> SecretsManager:
    global secrets_manager
    if not secrets_manager:
        raise Exception("SecretsManager não inicializado.")
    return secrets_manager

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
    arquivo_docx: Optional[UploadFile] = File(None),
    secrets_manager: SecretsManager = Depends(get_secrets_manager)
):
    logger.info(f"📥 [RECEPCIONISTA] Requisição recebida do backend para o job: {job_id}")

    blob_temp_path = None

    # Extrai o primeiro group_id se houver múltiplos
    first_group_id = None
    if group_ids:
        first_group_id = group_ids.split(",")[0].strip()

    # 1. TRATAR O ARQUIVO (Upload pro Azure Blob Storage)
    if arquivo_docx:
        try:
            creds = await secrets_manager.get_blob_storage_credentials(company_id, first_group_id)
            blob_service_client = BlobServiceClient.from_connection_string(creds["connection_string"])
            container_client = blob_service_client.get_container_client(creds["container_name"])
            
            # Cria o container de temporários se não existir
            if not await container_client.exists():
                await container_client.create_container()

            # Salva no blob com um nome único: jobid_nomearquivo.docx
            blob_name = f"{job_id}_{arquivo_docx.filename}"
            blob_client = container_client.get_blob_client(blob_name)
            
            # Lê os bytes e faz o upload
            conteudo = await arquivo_docx.read()
            await blob_client.upload_blob(conteudo, overwrite=True)
            
            blob_temp_path = f"{creds['container_name']}/{blob_name}"
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
        "documento_blob_path": blob_temp_path # A IA vai usar isso para baixar o arquivo depois
    }

    # 3. ENVIAR PARA A FILA DO AZURE
    try:
        creds = await secrets_manager.get_blob_storage_credentials(company_id, first_group_id)
        queue_client = QueueClient.from_connection_string(conn_str=creds["connection_string"], queue_name=QUEUE_NAME)
        
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

# ---------------------------------------------------------
# WORKER: O "Trabalhador" que lê da Fila em background
# ---------------------------------------------------------
async def process_queue_messages(secrets_manager: SecretsManager):
    """Fica rodando em loop puxando tarefas da fila e processando."""
    logger.info("👷 Worker iniciado e escutando a fila do Azure...")
    
    while True:
        try:
            # Para cada iteração, busca as credenciais da fila
            # Precisa de company_id e group_id para criar o QueueClient
            # Como não temos um job ainda, usamos um fallback para inicialização
            # (poderia ser um company_id padrão ou ignorar)
            # Aqui assume que o worker só processa quando há mensagens
            # Inicializa o cliente da fila com credenciais de um company_id genérico
            # (alternativamente, pode inicializar sem credenciais e criar por mensagem)
            creds = await secrets_manager.get_blob_storage_credentials("default", None)
            queue_client = QueueClient.from_connection_string(conn_str=creds["connection_string"], queue_name=QUEUE_NAME)
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
                            company_id = task_data.get('company_id')
                            group_ids = task_data.get('group_ids')
                            first_group_id = None
                            if group_ids:
                                first_group_id = group_ids.split(",")[0].strip()
                            logger.info(f"🔥 [WORKER] Pegou a tarefa! Iniciando job: {job_id} | Agente: {analysis_type}")
                            # Busca credenciais dinâmicas para Blob Storage
                            creds_msg = await secrets_manager.get_blob_storage_credentials(company_id, first_group_id)
                            blob_service_client = BlobServiceClient.from_connection_string(creds_msg["connection_string"])
                            container_client = blob_service_client.get_container_client(creds_msg["container_name"])
                            # ==========================================
                            # 2. AQUI ENTRA A SUA LÓGICA DE IA
                            # Você tem acesso a todos os parâmetros aqui:
                            # task_data.get('comentario_extra')
                            # task_data.get('email')
                            # task_data.get('documento_blob_path') -> Caminho para baixar o .docx se precisar
                            # ==========================================
                            await asyncio.sleep(5) # Simulando o processamento demorado da IA...
                            logger.info(f"✅ [WORKER] IA finalizou o job {job_id}.")
                            logger.info(f"🔔 [WORKER] Webhook disparado para o backend (job: {job_id}).")
                            await queue_client.delete_message(msg)
                            logger.info(f"🗑️ [WORKER] Mensagem do job {job_id} apagada da fila com sucesso.")
                    except Exception as e:
                        logger.error(f"Erro no loop do worker da fila: {e}")
                    await asyncio.sleep(3)
        except Exception as e:
            logger.error(f"Erro ao inicializar worker da fila: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
