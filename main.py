import logging
import uuid
import os
import asyncio
import httpx
from fastapi import FastAPI, APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

# --- CONFIGURAÇÃO ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MockMCP")

app = FastAPI(title="MCP Mock Service", version="1.0.7 - Strict Logic")
router = APIRouter()

# URL do Backend Principal (Ajuste se necessário)
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

# --- DADOS MOCKADOS (EXATAMENTE COMO SOLICITADO) ---

# Payload para: criacao_epicos_azure_devops
DATA_CRIACAO = {
    "epicos_report": {"epicos"[
        {"id": 1, "titulo": "Autenticação Azure AD", "descricao": "Implementar login seguro com OAuth2."},
        {"id": 2, "titulo": "Processamento de Arquivos", "descricao": "Ler e extrair texto de DOCX."},
        {"id": 3, "titulo": "Dashboard de Métricas", "descricao": "Visualizar status dos projetos."}
    ]
  }
}

# Payload para: refinamento_epicos_azure_devops
DATA_REFINAMENTO = {
    "epicos_report": {"epicos": {[
        {"id": 1, "titulo": "Autenticação Azure AD com maior atençao", "descricao": "Implementar login seguro com OAuth2. NONO"},
        {"id": 2, "titulo": "Processamento de Arquivos refinados", "descricao": "Ler e extrair texto de DOCX. NONO"},
        {"id": 3, "titulo": "Dashboard de Métricas refinados", "descricao": "Visualizar status dos projetos. NONO"}
    ]}
}

# --- LÓGICA DE ENVIO ---
async def send_result_to_backend(job_id: str, session_id: Optional[str], analysis_type: str):
    logger.info(f"⏳ [MOCK] Processando Job {job_id} para tipo: {analysis_type}...")
    await asyncio.sleep(3) # Simula o tempo de processamento
    
    # 1. SELEÇÃO DE DADOS (Lógica Estrita)
    if analysis_type == "refinamento_epicos_azure_devops":
        logger.info("👉 Selecionando dados de REFINAMENTO")
        report_data = DATA_REFINAMENTO
        # O backend espera "epicos" ou "refinamento_epicos" no report_type? 
        # Geralmente se o JSON é "epicos_report", o type é "epicos", mas mantive mapeado:
        report_type = "epicos" 
    else:
        # Default para criacao ou qualquer outro caso
        logger.info("👉 Selecionando dados de CRIAÇÃO")
        report_data = DATA_CRIACAO
        report_type = "epicos"

    async with httpx.AsyncClient(timeout=15.0) as client:
        headers = {"Content-Type": "application/json"}
        base_url = BACKEND_BASE_URL.rstrip('/')

        # =========================================================
        # TENTATIVA 1: Via Webhook Oficial
        # =========================================================
        webhook_payload = {
            "job_id": job_id,
            "status": "done",
            "report_type": report_type,
            "report_data": report_data
        }
        
        logger.info(f"📤 [WEBHOOK] Enviando para {base_url}/webhooks/mcp")
        logger.info(f"📦 Payload parcial: {str(report_data)[:100]}...")

        try:
            resp = await client.post(f"{base_url}/webhooks/mcp", json=webhook_payload, headers=headers)
            
            if resp.status_code == 200:
                logger.info("✅ [SUCESSO] Webhook aceito pelo Backend!")
                return 
            
            logger.warning(f"⚠️ [ALERTA] Webhook falhou: {resp.status_code} - {resp.text}")
            
        except Exception as e:
            logger.error(f"❌ Erro de conexão no Webhook: {e}")

        # =========================================================
        # TENTATIVA 2: Fallback via Sessão
        # =========================================================
        if session_id:
            logger.info("🔄 [FALLBACK] Salvando direto na Sessão...")
            
            direct_payload = {
                "report_type": report_type,
                "report_data": report_data
            }
            
            try:
                resp = await client.put(f"{base_url}/session/{session_id}/report", json=direct_payload, headers=headers)
                if resp.status_code == 200:
                    logger.info("✅ [SALVO] Dados salvos via Fallback de Sessão.")
                else:
                    logger.error(f"❌ [FALHA TOTAL] Fallback falhou: {resp.status_code}")
            except Exception as e:
                logger.error(f"❌ Erro conexão Fallback: {e}")
        else:
            logger.error("🚫 Sem session_id para tentar o Fallback.")

# --- ENDPOINTS ---

@router.get("/")
def home():
    return {"status": "Mock MCP Online v1.0.7", "target": BACKEND_BASE_URL}

@router.post("/start")
async def start_analysis_mock(payload: FakeMCPStartPayload, background_tasks: BackgroundTasks):
    current_job_id = payload.job_id or f"job-mock-{uuid.uuid4().hex[:8]}"
    
    logger.info(f"⚡ [MOCK] Start recebido. Tipo: {payload.analysis_type} | Job: {current_job_id}")

    # Agenda o envio
    background_tasks.add_task(
        send_result_to_backend, 
        current_job_id, 
        payload.session_id, 
        payload.analysis_type
    )

    return {
        "job_id": current_job_id,
        "status": "queued",
        "message": "Análise iniciada. Mock responderá em ~3 segundos."
    }

app.include_router(router, prefix="/fake-mcp/api/v1/analysis")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
