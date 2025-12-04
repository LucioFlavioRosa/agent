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

app = FastAPI(title="MCP Mock Service", version="1.0.1")
router = APIRouter()

# URL do Backend Principal (Ajuste conforme necessário)
BACKEND_BASE_URL = os.environ.get("TARGET_BACKEND_URL", "https://app-codeai-backend-dev-usc-fngga4fkbkewewdz.centralus-01.azurewebsites.net")

# --- MODELOS ---
class FakeMCPStartPayload(BaseModel):
    projeto: str
    analysis_type: str
    arquivo_docx: Optional[str] = None
    comentario_usuario: Optional[str] = None
    usuario_executor: Optional[str] = None
    session_id: Optional[str] = None
    # Adicionado job_id caso o backend passe, mas vamos gerar se não vier
    job_id: Optional[str] = None 

# --- DADOS MOCKADOS (Conteúdo interno do report_data) ---
MOCK_DATA_CONTENT = {
    "epicos": {
        "epicos": [
            {"id": 1, "titulo": "Autenticação Azure AD", "descricao": "Implementar fluxo OAuth2."},
            {"id": 2, "titulo": "Processamento de Arquivos", "descricao": "Ler DOCX via Azure Functions."}
        ]
    },
    "features": {
        "features": [
            {"id": 1, "nome": "Login Social", "descricao": "Permitir Google e Microsoft."}
        ]
    },
    "tech_debt": {
        "tech_debt": [
            {"id": 1, "descricao": "Refatorar Controller de Upload", "prioridade": "Alta"}
        ]
    }
}

# --- MAPEAMENTO (Analysis Type -> Report Type) ---
# Conforme seção 2.6 da sua documentação
ANALYSIS_MAPPING = {
    "criacao_epicos_azure_devops": "epicos",
    "features_generation": "features",
    "tech_debt_analysis": "tech_debt"
}

# --- LÓGICA DE CALLBACK (WEBHOOK) ---
async def simulate_webhook_callback(job_id: str, analysis_type: str):
    """
    Simula o processamento e envia o Webhook para o Backend seguindo o formato oficial.
    """
    logger.info(f"⏳ [MOCK] Processando Job {job_id}... (Aguardando 3s)")
    await asyncio.sleep(3)
    
    # 1. Determina o report_type baseado no analysis_type
    report_type = ANALYSIS_MAPPING.get(analysis_type, "generic")
    
    # 2. Seleciona os dados correspondentes
    report_data = MOCK_DATA_CONTENT.get(report_type, {"message": "Dados genéricos gerados."})
    
    # 3. Monta o Payload do Webhook (Seção 2.1 da doc)
    webhook_payload = {
        "job_id": job_id,
        "status": "done",         # ou "in_progress"
        "report_type": report_type,
        "report_data": report_data
        # "error_type": null (não enviamos em caso de sucesso)
    }

    # 4. Define o Endpoint do Webhook
    webhook_url = f"{BACKEND_BASE_URL.rstrip('/')}/webhooks/mcp"
    
    logger.info(f"📤 [MOCK] Enviando Webhook para: {webhook_url}")
    logger.info(f"📦 Payload: {webhook_payload}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Headers simulando envio interno/seguro
            headers = {
                "Content-Type": "application/json",
                # Se seu backend valida tokens entre serviços, adicione aqui.
                # Como é teste e você tem IP Allowlist ou bypass, pode não precisar.
            }
            
            resp = await client.post(webhook_url, json=webhook_payload, headers=headers)
            
            if resp.status_code == 200:
                logger.info(f"✅ [MOCK] Webhook entregue com sucesso! Backend respondeu 200.")
            else:
                logger.error(f"❌ [MOCK] Falha no Webhook: {resp.status_code} - {resp.text}")
                
    except Exception as e:
        logger.error(f"❌ [MOCK] Erro de conexão ao chamar Backend: {e}")

# --- ENDPOINTS ---

@router.get("/")
def home():
    return {"status": "Mock MCP Online", "target_backend": BACKEND_BASE_URL}

@router.post("/start")
async def start_analysis_mock(payload: FakeMCPStartPayload, background_tasks: BackgroundTasks):
    # Se o backend não mandou job_id, geramos um novo aqui
    job_id = payload.job_id if payload.job_id else f"job-mock-{uuid.uuid4().hex[:8]}"
    
    logger.info(f"⚡ [MOCK] Recebi pedido de análise!")
    logger.info(f"   Projeto: {payload.projeto} | Tipo: {payload.analysis_type}")
    logger.info(f"   Job ID atribuído: {job_id}")

    # Agenda o envio do Webhook (Background)
    # IMPORTANTE: Passamos o job_id para o callback saber quem atualizar
    background_tasks.add_task(
        simulate_webhook_callback, 
        job_id, 
        payload.analysis_type
    )

    # Resposta síncrona imediata para o Backend (Backend recebe isso e guarda o job_id)
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
