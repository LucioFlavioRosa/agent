import logging
import uuid
import os
import asyncio
import httpx
from fastapi import FastAPI, APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any

# --- CONFIGURAÇÃO ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MockMCP")

app = FastAPI(title="MCP Mock Service", version="1.0.2")
router = APIRouter()

# URL do Backend Principal
BACKEND_BASE_URL = os.environ.get("TARGET_BACKEND_URL", "https://app-codeai-backend-dev-usc-fngga4fkbkewewdz.centralus-01.azurewebsites.net")

# --- MODELOS ---
class FakeMCPStartPayload(BaseModel):
    projeto: str
    analysis_type: str
    arquivo_docx: Optional[str] = None
    comentario_usuario: Optional[str] = None
    usuario_executor: Optional[str] = None
    session_id: Optional[str] = None
    job_id: Optional[str] = None 

# --- DADOS MOCKADOS (Exatamente como na Spec 2.2.2) ---
MOCK_DATA_CONTENT = {
    # Caso: report_type = "epicos"
    "epicos": {
        "epicos": [
            {"id": 1, "titulo": "Como usuário...", "descricao": "Quero realizar login no sistema para acessar meus projetos."},
            {"id": 2, "titulo": "Como admin...", "descricao": "Quero visualizar relatórios de uso da plataforma."}
        ]
    },
    # Caso: report_type = "features"
    "features": {
        "features": [
            {"id": 1, "nome": "Login SSO", "descricao": "Integração com Azure AD"}
        ]
    },
    # Caso: report_type = "tech_debt"
    "tech_debt": {
        "tech_debt": [
            {"id": 1, "descricao": "Refatoração de logs", "prioridade": "média"}
        ]
    }
}

# --- MAPEAMENTO (Analysis Type -> Report Type) ---
# Converte o tipo de análise do backend para o tipo de relatório esperado no webhook
ANALYSIS_MAPPING = {
    "criacao_epicos_azure_devops": "epicos",
    "features_generation": "features",
    "tech_debt_analysis": "tech_debt"
}

# --- LÓGICA DE CALLBACK (WEBHOOK) ---
async def simulate_webhook_callback(job_id: str, analysis_type: str):
    """
    Simula o processamento e envia o Webhook POST para /webhooks/mcp
    """
    logger.info(f"⏳ [MOCK] Processando Job {job_id}... (Aguardando 3s)")
    await asyncio.sleep(3)
    
    # 1. Determina o report_type correto (Seção 2.6)
    report_type = ANALYSIS_MAPPING.get(analysis_type, "epicos") # Default para epicos se não achar
    
    # 2. Seleciona os dados (Seção 2.3)
    # report_data conterá: { "epicos": [ ... ] }
    report_data = MOCK_DATA_CONTENT.get(report_type)
    if not report_data:
        # Fallback de segurança
        report_data = {"epicos": [{"id": 99, "titulo": "Fallback", "descricao": "Erro no mock"}]}

    # 3. Monta o Payload do Webhook (Seção 2.1 e 2.2.2)
    # status: done -> progress removido, error removido.
    webhook_payload = {
        "job_id": job_id,
        "status": "done", 
        "report_type": report_type,
        "report_data": report_data
    }

    # 4. Define o Endpoint
    webhook_url = f"{BACKEND_BASE_URL.rstrip('/')}/webhooks/mcp"
    
    logger.info(f"📤 [MOCK] Enviando para: {webhook_url}")
    logger.info(f"📦 Payload JSON: {webhook_payload}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Headers padrão
            headers = {"Content-Type": "application/json"}
            
            # ENVIO POST
            resp = await client.post(webhook_url, json=webhook_payload, headers=headers)
            
            if resp.status_code == 200:
                logger.info(f"✅ [MOCK] Sucesso! Backend respondeu 200 OK.")
            else:
                logger.error(f"❌ [MOCK] Falha: {resp.status_code} - {resp.text}")
                
    except Exception as e:
        logger.error(f"❌ [MOCK] Erro de conexão: {e}")

# --- ENDPOINTS DO MOCK ---

@router.get("/")
def home():
    return {"status": "Mock MCP Online v1.0.2", "target": BACKEND_BASE_URL}

@router.post("/start")
async def start_analysis_mock(payload: FakeMCPStartPayload, background_tasks: BackgroundTasks):
    # Usa o job_id vindo do backend, ou gera um se for teste manual direto no mock
    job_id = payload.job_id if payload.job_id else f"job-mock-{uuid.uuid4().hex[:8]}"
    
    logger.info(f"⚡ [MOCK] Requisição Recebida | Job ID: {job_id}")

    # Agenda a tarefa assíncrona para simular o tempo de processamento
    background_tasks.add_task(
        simulate_webhook_callback, 
        job_id, 
        payload.analysis_type
    )

    # Retorna confirmação imediata
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Job aceito. Webhook será enviado em breve."
    }

# Registra a rota
app.include_router(router, prefix="/fake-mcp/api/v1/analysis")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
