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

app = FastAPI(title="MCP Mock Service", version="1.0.0")
router = APIRouter()

# ⚠️ IMPORTANTE: Configure esta variável no Azure do MOCK para apontar para o BACKEND
# Exemplo: https://app-codeai-backend-dev-usc.azurewebsites.net
BACKEND_BASE_URL = os.environ.get("TARGET_BACKEND_URL", "https://SEU-BACKEND-PRINCIPAL.azurewebsites.net")

# --- MODELOS ---
class FakeMCPStartPayload(BaseModel):
    projeto: str
    analysis_type: str
    arquivo_docx: Optional[str] = None
    comentario_usuario: Optional[str] = None
    usuario_executor: Optional[str] = None
    session_id: Optional[str] = None

# --- DADOS MOCKADOS (A "Inteligência" Falsa) ---
MOCK_RESPONSES = {
    "criacao_epicos_azure_devops": {
        # O backend usa 'report_type' para saber o que fazer. 
        # Enviamos o próprio analysis_type para garantir que ele carregue a config correta.
        "report_type": "criacao_epicos_azure_devops", 
        "report_data": {
            # CHAVE 1: 'epicos' (Para satisfazer o report_mapping: {"epicos": "epicos_report"})
            "epicos": [
                {"id": 1, "titulo": "Autenticação Segura (Via Mapping)", "descricao": "Login via Azure AD."},
                {"id": 2, "titulo": "Upload de Arquivos", "descricao": "Processamento de DOCX."}
            ],
            # CHAVE 2: 'epicos_report' (Backup caso o backend salve direto sem mapping)
            "epicos_report": [
                {"id": 1, "titulo": "Autenticação Segura (Direto)", "descricao": "Login via Azure AD."},
                {"id": 2, "titulo": "Upload de Arquivos", "descricao": "Processamento de DOCX."}
            ]
        }
    },
    "default": {
        "report_type": "generic",
        "report_data": {"message": "Análise genérica concluída."}
    }
}

# --- LÓGICA DE CALLBACK (WEBHOOK) ---
async def simulate_webhook_callback(session_id: str, analysis_type: str):
    """
    Simula o processamento e envia os dados de volta para o Backend Principal.
    """
    logger.info(f"⏳ [MOCK] Processando... (Aguardando 3s)")
    await asyncio.sleep(3)
    
    # 1. Seleciona os dados
    mock_content = MOCK_RESPONSES['criacao_epicos_azure_devops']
    
    # 2. Monta a URL do Webhook no Backend Principal
    # O Mock (Slot B) chama o Backend (Slot A)
    callback_url = f"{BACKEND_BASE_URL.rstrip('/')}/session/{session_id}/report"
    
    logger.info(f"📤 [MOCK] Enviando Callback para: {callback_url}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Enviamos headers simulando autorização se necessário, 
            # ou confiamos que o Backend aceita chamadas internas/liberadas por IP
            headers = {
                "Content-Type": "application/json",
                "X-Test-User-Json": '{"sub": "mock-service"}' # Bypass simples se necessário
            }
            
            resp = await client.put(callback_url, json=mock_content, headers=headers)
            
            if resp.status_code == 200:
                logger.info(f"✅ [MOCK] Webhook entregue com sucesso!")
            else:
                logger.error(f"❌ [MOCK] Falha no Webhook: {resp.status_code} - {resp.text}")
                
    except Exception as e:
        logger.error(f"❌ [MOCK] Erro de conexão ao chamar Backend: {e}")

# --- ENDPOINTS ---

@router.get("/")
def home():
    return {"status": "Mock Service Online", "target_backend": BACKEND_BASE_URL}

@router.post("/start")
async def start_analysis_mock(payload: FakeMCPStartPayload, background_tasks: BackgroundTasks):
    job_id = f"job-ext-{uuid.uuid4().hex[:8]}"
    
    logger.info(f"⚡ [MOCK] Recebi chamada do Backend!")
    logger.info(f"📂 Projeto: {payload.projeto} | Session: {payload.session_id}")

    if payload.session_id:
        # Agenda o envio da resposta para daqui a pouco (Background)
        background_tasks.add_task(
            simulate_webhook_callback, 
            payload.session_id, 
            payload.analysis_type
        )
    else:
        logger.warning("⚠️ [MOCK] Sem session_id, não haverá callback.")

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
