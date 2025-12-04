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

app = FastAPI(title="MCP Mock Service", version="1.0.6 - Final Fix")
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

# --- DADOS MOCKADOS (AQUI ESTAVA O SEGREDO) ---
MOCK_DATA_CONTENT = {
    "epicos": {
        "epicos_report": [
            {"id": 1, "titulo": "Autenticação Azure AD", "descricao": "Implementar login seguro com OAuth2."},
            {"id": 2, "titulo": "Processamento de Arquivos", "descricao": "Ler e extrair texto de DOCX."},
            {"id": 3, "titulo": "Dashboard de Métricas", "descricao": "Visualizar status dos projetos."}
        ]
    },
    "refinamento_epicos": {
        "epicos_report": [
            {"id": 1, "titulo": "Autenticação Azure AD_eeeee", "descricao": "Implementar login seguro com OAuth2. NONO"},
            {"id": 2, "titulo": "Processamento de Arquivos_eeeeee", "descricao": "Ler e extrair texto de DOCX. NONO"},
            {"id": 3, "titulo": "Dashboard de Métricas_eeeeeee", "descricao": "Visualizar status dos projetos. NONO"}
        ]
    }
}

ANALYSIS_MAPPING = {
    "criacao_epicos_azure_devops": "epicos",
    "refinamento_epicos_azure_devops": "refinamento_epicos"
}

# --- LÓGICA DE ENVIO (COM DUPLA SEGURANÇA) ---
async def send_result_to_backend(job_id: str, session_id: Optional[str], analysis_type: str):
    logger.info(f"⏳ [MOCK] Processando Job {job_id}...")
    await asyncio.sleep(3) # Simula o tempo de 'pensar' da IA
    
    # 1. Seleciona o tipo correto de relatório
    report_type = ANALYSIS_MAPPING.get(analysis_type, "epicos")
    
    # 2. Pega os dados com a estrutura correta (epicos_report)
    report_data = MOCK_DATA_CONTENT.get(report_type) 

    async with httpx.AsyncClient(timeout=15.0) as client:
        headers = {"Content-Type": "application/json"}
        base_url = BACKEND_BASE_URL.rstrip('/')

        # =========================================================
        # TENTATIVA 1: Via Webhook Oficial (O Jeito Certo)
        # =========================================================
        webhook_payload = {
            "job_id": job_id,
            "status": "done",
            "report_type": report_type,
            "report_data": report_data
        }
        
        logger.info(f"📤 [TENTATIVA 1] Enviando Webhook para {base_url}/webhooks/mcp")
        try:
            resp = await client.post(f"{base_url}/webhooks/mcp", json=webhook_payload, headers=headers)
            
            if resp.status_code == 200:
                logger.info("✅ [SUCESSO] Webhook aceito pelo Backend com chave 'epicos_report'!")
                return # Missão cumprida, encerra aqui.
            
            logger.warning(f"⚠️ [ALERTA] Webhook falhou: {resp.status_code} - {resp.text}")
            
        except Exception as e:
            logger.error(f"❌ Erro de conexão no Webhook: {e}")

        # =========================================================
        # TENTATIVA 2: Fallback via Sessão (O Plano B)
        # Se o Webhook falhar (ex: 404 Job não encontrado), salvamos direto na sessão.
        # =========================================================
        if session_id:
            logger.info("🔄 [TENTATIVA 2] Tentando salvar direto na Sessão...")
            
            # O endpoint de sessão geralmente espera { "report_type": ..., "report_data": ... }
            direct_payload = {
                "report_type": report_type,
                "report_data": report_data
            }
            
            try:
                resp = await client.put(f"{base_url}/session/{session_id}/report", json=direct_payload, headers=headers)
                if resp.status_code == 200:
                    logger.info("✅ [SALVO] Dados salvos via Fallback de Sessão.")
                else:
                    logger.error(f"❌ [FALHA TOTAL] Nem o fallback funcionou: {resp.status_code}")
            except Exception as e:
                logger.error(f"❌ Erro conexão Fallback: {e}")
        else:
            logger.error("🚫 Sem session_id para tentar o Fallback.")

# --- ENDPOINTS ---

@router.get("/")
def home():
    return {"status": "Mock MCP Online v1.0.6", "target": BACKEND_BASE_URL}

@router.post("/start")
async def start_analysis_mock(payload: FakeMCPStartPayload, background_tasks: BackgroundTasks):
    # Usa o Job ID do backend ou cria um
    current_job_id = payload.job_id or f"job-mock-{uuid.uuid4().hex[:8]}"
    
    logger.info(f"⚡ [MOCK] Start recebido. Job: {current_job_id} | Sessão: {payload.session_id}")

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
