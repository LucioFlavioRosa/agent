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

app = FastAPI(title="MCP Mock Service", version="1.0.9 - Timeout Fix")
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

# --- DADOS MOCKADOS ---
DATA_CRIACAO = {
    "epicos_report": {
        "epicos": [
            {"id": 1, "titulo": "Autenticação Azure AD", 
             "descricao": "Implementar login seguro com OAuth2. Vou testar Algumas coisas", 
             "tempo estimado": "2 sprint", "criterios de aceite": 
             "eu preciso fazer esse login de qualquer maquina"},
            {"id": 2, "titulo": "Processamento de Arquivos", 
             "descricao": "Ler e extrair texto de DOCX."},
            {"id": 3, "titulo": "Dashboard de Métricas", "descricao": "Visualizar status dos projetos."}
        ]
    }
}

DATA_REFINAMENTO = {
    "epicos_report": {
        "epicos": [
            {"id": 1, "titulo": "Autenticação Azure AD com maior atençao", "descricao": "Implementar login seguro com OAuth2. NONO"},
            {"id": 2, "titulo": "Processamento de Arquivos refinados", "descricao": "Ler e extrair texto de DOCX. NONO"},
            {"id": 3, "titulo": "Dashboard de Métricas refinados", "descricao": "Visualizar status dos projetos. NONO"}
        ]
    }
}

FEATURE_CRIACAO = {
    "features_report": {
        "features": [
            {"feature id": 1, "epico id ": "1", "titulo": "setup infra na nuvem", "prazo": "2 dias"},
            {"feature id": 2, "epico id ": "2", "titulo": "testes de segurança", "prazo": "1 dia"}
        ]
    }
}

# --- LÓGICA DE ENVIO ---
async def send_result_to_backend(job_id: str, session_id: Optional[str], analysis_type: str):
    logger.info(f"⏳ [MOCK] Aguardando 3s antes de enviar resultado para Job {job_id}...")
    await asyncio.sleep(3) 
    
    # 1. SELEÇÃO DE DADOS
    if analysis_type == "refinamento_epicos_azure_devops":
        logger.info("👉 Selecionando dados de REFINAMENTO")
        report_data = DATA_REFINAMENTO
        report_type = "epicos" 
    if analysis_type == "criacao_features_azure_devops":
        logger.info("👉 Selecionando dados de FEATURES")
        report_data = FEATURE_CRIACAO
        report_type = "features" 
    else:
        logger.info("👉 Selecionando dados de CRIAÇÃO")
        report_data = DATA_CRIACAO
        report_type = "epicos"

    # Aumentei o timeout para 30s para evitar erro se o backend estiver lento ("Cold Start" do backend)
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"Content-Type": "application/json"}
        base_url = BACKEND_BASE_URL.rstrip('/')

        webhook_payload = {
            "session_id": session_id,
            "job_id": job_id,
            "status": "done",
            "report_type": report_type,
            "report_data": report_data
        }
        
        logger.info(f"📤 [WEBHOOK] Tentando enviar para {base_url}/webhooks/mcp")
        
        try:
            resp = await client.post(f"{base_url}/webhooks/mcp", json=webhook_payload, headers=headers)
            
            if resp.status_code == 200:
                logger.info("✅ [SUCESSO] Webhook aceito pelo Backend!")
                return 
            
            logger.warning(f"⚠️ [FALHA WEBHOOK] Status: {resp.status_code} - Body: {resp.text}")
            
        except httpx.TimeoutException:
            logger.error("❌ [TIMEOUT] O Backend demorou mais de 30s para responder ao Webhook.")
        except Exception as e:
            logger.error(f"❌ [ERRO CONEXÃO] {e}")

        # TENTATIVA 2: Fallback
        if session_id:
            logger.info("🔄 [FALLBACK] Tentando salvar direto na Sessão...")
            direct_payload = {"report_type": report_type, "report_data": report_data}
            try:
                resp = await client.put(f"{base_url}/session/{session_id}/report", json=direct_payload, headers=headers)
                if resp.status_code == 200:
                    logger.info("✅ [SALVO VIA SESSION] Fallback funcionou.")
                else:
                    logger.error(f"❌ [FALHA FALLBACK] Status: {resp.status_code}")
            except Exception as e:
                logger.error(f"❌ [ERRO FALLBACK] {e}")

# --- ENDPOINTS ---

@router.get("/")
def home():
    return {"status": "Mock MCP Online v1.0.9", "target": BACKEND_BASE_URL}

@router.post("/start")
async def start_analysis_mock(payload: FakeMCPStartPayload, background_tasks: BackgroundTasks):
    # CORREÇÃO: Usamos o job_id enviado ou criamos um novo. Não usamos o session_id como job_id para evitar confusão.
    current_job_id = payload.job_id or f"job-mock-{uuid.uuid4().hex[:8]}"
    
    logger.info(f"⚡ [MOCK] Start recebido. Sessão: {payload.session_id} | Job: {current_job_id}")

    # Agenda o envio em background (Isso evita timeout na resposta do /start)
    background_tasks.add_task(
        send_result_to_backend, 
        current_job_id, 
        payload.session_id, 
        payload.analysis_type
    )

    return {
        "job_id": current_job_id,
        "session_id": payload.session_id, # Campo obrigatório para o seu teste
        "status": "queued",
        "message": "Análise iniciada. Mock responderá em breve."
    }

app.include_router(router, prefix="/fake-mcp/api/v1/analysis")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    # Workers = 1 é suficiente para mock, mas garante que não cria processos zumbis
    uvicorn.run(app, host="0.0.0.0", port=port)
