import logging
import uuid
import os
import asyncio
import httpx
from fastapi import FastAPI, APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

# --- CONFIGURAÇÃO ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MockMCP")

app = FastAPI(title="MCP Mock Service", version="2.0.0 - Peers CodeAI Spec")
router = APIRouter()

# URL do Backend Principal (Ajuste conforme necessário ou use variável de ambiente)
BACKEND_BASE_URL = os.environ.get("TARGET_BACKEND_URL", "http://localhost:8000")

# --- MODELOS (Baseado na doc: "Payload enviado do backend para o MCP") ---
class MCPStartPayload(BaseModel):
    projeto: str
    analysis_type: str
    arquivo_docx: Optional[str] = None
    comentario_usuario: Optional[str] = None
    usuario_executor: Optional[str] = None
    project_id: str  # Obrigatório conforme doc
    nome_projeto: Optional[str] = None

# --- DADOS MOCKADOS ---

# Cenário 1: Criação de Épicos
DATA_EPICOS = {
    "epicos_report": [
        {
            "id": 1, 
            "titulo": "Autenticação e Segurança", 
            "descricao": "Implementar login via Azure AD e gestão de segredos.",
            "criterios_aceite": "Login funcional, Token JWT validado.",
            "prioridade": "Alta"
        },
        {
            "id": 2, 
            "titulo": "Processamento de Documentos", 
            "descricao": "Upload e extração de texto de arquivos DOCX.",
            "criterios_aceite": "Texto extraído corretamente, Arquivo salvo no Blob.",
            "prioridade": "Alta"
        }
    ]
}

# Cenário 2: Features (Baseado no épico de autenticação)
DATA_FEATURES = {
    "features_report": [
        {"id": 101, "epico_id": 1, "nome": "Configurar App Registration Azure", "descricao": "Criar app no entra ID"},
        {"id": 102, "epico_id": 1, "nome": "Middleware de Validação JWT", "descricao": "Validar token no backend Python"},
        {"id": 103, "epico_id": 2, "nome": "Integração python-docx", "descricao": "Serviço de parser"}
    ]
}

# Cenário 3: Tech Debt / Riscos
DATA_RISCOS = {
    "premissas_riscos_report": [
        {"id": 1, "tipo": "Risco", "descricao": "Latência alta na comunicação com MCP se não houver timeout configurado."},
        {"id": 2, "tipo": "Premissa", "descricao": "O Redis estará disponível na VNET privada."}
    ]
}

# --- LÓGICA DE ENVIO ---
async def process_and_send_webhook(job_id: str, project_id: str, analysis_type: str):
    logger.info(f"⏳ [MOCK] Processando Job {job_id} para Projeto {project_id} ({analysis_type})...")
    
    # Simula tempo de processamento
    await asyncio.sleep(5) 
    
    # 1. SELEÇÃO DE DADOS BASEADA NO TIPO DE ANÁLISE
    report_data = {}
    
    if "features" in analysis_type:
        logger.info("👉 Selecionando dados de FEATURES")
        report_data = DATA_FEATURES
    elif "riscos" in analysis_type or "tech_debt" in analysis_type:
        logger.info("👉 Selecionando dados de RISCOS")
        report_data = DATA_RISCOS
    else:
        # Default para épicos ou qualquer outro
        logger.info("👉 Selecionando dados de ÉPICOS (Default)")
        report_data = DATA_EPICOS

    # 2. PREPARAÇÃO DO PAYLOAD DO WEBHOOK (Conforme Doc 2.1)
    webhook_payload = {
        "job_id": job_id,
        "project_id": project_id,
        "status": "done",
        # O report_data já contém a chave correta (ex: 'epicos_report') dentro dele
        "report_data": report_data 
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        base_url = BACKEND_BASE_URL.rstrip('/')
        webhook_url = f"{base_url}/webhooks/mcp"
        
        logger.info(f"📤 [WEBHOOK] Enviando para {webhook_url}")
        
        try:
            # TENTATIVA 1: Webhook Padrão
            resp = await client.post(webhook_url, json=webhook_payload)
            
            if resp.status_code == 200:
                logger.info(f"✅ [SUCESSO] Webhook recebido pelo Backend! (Job: {job_id})")
                return 
            
            logger.warning(f"⚠️ [FALHA WEBHOOK] Status: {resp.status_code} - Body: {resp.text}")
            
        except Exception as e:
            logger.error(f"❌ [ERRO CONEXÃO] {e}")

        # TENTATIVA 2: Fallback (PUT direto na sessão conforme Doc 1.5)
        # URL Correta: /session/project/{project_id}/report
        fallback_url = f"{base_url}/session/project/{project_id}/report"
        logger.info(f"🔄 [FALLBACK] Tentando endpoint direto: {fallback_url}")
        
        # O endpoint de report espera { "report_data": { ... } }
        fallback_payload = { "report_data": report_data }
        
        try:
            resp = await client.put(fallback_url, json=fallback_payload)
            if resp.status_code == 200:
                logger.info("✅ [SALVO VIA PUT] Fallback funcionou.")
            else:
                logger.error(f"❌ [FALHA FALLBACK] Status: {resp.status_code} - {resp.text}")
        except Exception as e:
            logger.error(f"❌ [ERRO FALLBACK] {e}")

# --- ENDPOINTS ---

@router.get("/")
def home():
    return {
        "status": "Mock MCP Online v2.1", 
        "routes": ["/start", "/api/v1/analysis/start"],
        "target_backend": BACKEND_BASE_URL
    }

@router.post("/start")
async def start_analysis(payload: MCPStartPayload, background_tasks: BackgroundTasks):
    # ... (código da função start_analysis permanece igual) ...
    # Gera um Job ID único para esta execução
    new_job_id = str(uuid.uuid4())
    
    logger.info(f"⚡ [START] Recebido para Project ID: {payload.project_id}")

    background_tasks.add_task(
        process_and_send_webhook,
        job_id=new_job_id,
        project_id=payload.project_id,
        analysis_type=payload.analysis_type
    )

    return {
        "message": "Análise solicitada com sucesso ao agente (MOCK).",
        "job_id": new_job_id,
        "project_id": payload.project_id,
        "nome_projeto": payload.nome_projeto or "Projeto Desconhecido"
    }

# ==============================================================================
# CORREÇÃO AQUI: Registrar o router em DOIS lugares para garantir compatibilidade
# ==============================================================================

# 1. Registra para funcionar se o Backend chamar a URL completa (ex: .../api/v1/analysis/start)
app.include_router(router, prefix="/api/v1/analysis") 

# 2. Registra TAMBÉM na raiz para funcionar se o Backend chamar direto (ex: .../start)
app.include_router(router, prefix="") 

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
