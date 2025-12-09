import logging
import uuid
import os
import asyncio
import httpx
from fastapi import FastAPI, APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

# --- CONFIGURAÇÃO ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MockMCP")

app = FastAPI(title="MCP Mock Service", version="2.3.0 - Fixed Webhook Spec")
router = APIRouter()

# URL do Backend Principal (Deve ser configurada nas Variáveis de Ambiente do Azure)
BACKEND_BASE_URL = os.environ.get("TARGET_BACKEND_URL", "http://localhost:8000")

# --- MODELOS ---
class MCPStartPayload(BaseModel):
    project_id: str 
    analysis_type: str
    instrucoes_extras: Optional[str] = None 
    arquivo_docx: Optional[str] = None
    nome_projeto: Optional[str] = None 
    usuario_executor: Optional[str] = None

# --- DADOS MOCKADOS ---
DATA_EPICOS = {
    "epicos_report": [
        { "id": 1, "titulo": "Autenticação e Segurança", "descricao": "Implementar login via Azure AD.", "prioridade": "Alta" },
        { "id": 2, "titulo": "Processamento de Documentos", "descricao": "Upload e extração de texto.", "prioridade": "Alta" }
    ]
}

DATA_EPICOS_REFINAMENTO = {
    "epicos_report": [
        { "id": 1, "titulo": "Autenticação e Segurança - Fase 1", 
         "descricao": "Implementar login via Azure AD single-tenant.", "prioridade": "Alta" },
        { "id": 2, "titulo": "Processamento de Documentos", "descricao": "Upload e extração de texto.", "prioridade": "Alta" }
    ]
}

DATA_FEATURES = {
    "features_report": [
        {"id": 101, "epico_id": 1, "nome": "Configurar App Registration Azure", "descricao": "Criar app no Entra ID"},
        {"id": 102, "epico_id": 1, "nome": "Middleware de Validação JWT", "descricao": "Validar token no backend Python"}
    ]
}

DATA_FEATURES_REFINAMENTO = {
    "features_report": [
        {"id": 101, "epico_id": 1, "nome": "Configurar App Registration Azure", 
         "descricao": "Criar app no Entra ID",
        "critério_de_aceite": "Usuários do domínio da empresa devem conseguir logar."},
        {"id": 102, "epico_id": 1, "nome": "Middleware de Validação JWT", 
         "descricao": "Validar token no backend Python"}
    ]
}

DATA_RISCOS = {
    "premissas_riscos_report": [
        {"id": 1, "tipo": "Risco", "descricao": "Latência alta na comunicação entre serviços."},
        {"id": 2, "tipo": "Premissa", "descricao": "Redis disponível na VNET."}
    ]
}

# --- LÓGICA DE ENVIO ---
async def process_and_send_webhook(job_id: str, project_id: str, analysis_type: str):
    logger.info(f"⏳ [MOCK] Processando Job {job_id} para Projeto {project_id} ({analysis_type})...")
    
    # 1. Simula tempo de processamento da IA
    await asyncio.sleep(5) 
    
    status = "done"
    report_data = {}
    error_payload = {}

    # 2. Lógica de Erro Simulado
    if "erro_teste" in analysis_type:
        status = "error"
        error_payload = {
            "error_type": "simulation_error",
            "error_message": "Erro simulado pelo Mock MCP para teste de resiliência."
        }
    else:
        # 3. Seleção de Dados Mockados
        if "criacao_features" in analysis_type:
            report_data = DATA_FEATURES
        elif "refinamento_features" in analysis_type:
            report_data = DATA_FEATURES_REFINAMENTO
        elif "criacao_epicos" in analysis_type:
            report_data = DATA_EPICOS
        elif "refinamento_epicos" in analysis_type:
            report_data = DATA_EPICOS_REFINAMENTO
        elif "riscos" in analysis_type or "tech_debt" in analysis_type:
            report_data = DATA_RISCOS
        else:
            # Default fallback se o tipo for desconhecido
            report_data = DATA_EPICOS 
        

    # 4. PREPARAÇÃO DO PAYLOAD (CORRIGIDO)
    webhook_payload = {
        "job_id": job_id,
        "project_id": project_id,
        "status": status,
        "analysis_type": analysis_type  # <--- CORREÇÃO CRÍTICA AQUI: O Backend exige isso para rotear o relatório
    }

    if status == "done":
        webhook_payload["report_data"] = report_data
    elif status == "error":
        webhook_payload.update(error_payload)

    # 5. Envio do Webhook
    async with httpx.AsyncClient(timeout=30.0) as client:
        base_url = BACKEND_BASE_URL.rstrip('/')
        webhook_url = f"{base_url}/webhooks/mcp"
        
        logger.info(f"📤 [WEBHOOK] Enviando para {webhook_url}")
        
        try:
            # TENTATIVA 1: Webhook Padrão
            resp = await client.post(webhook_url, json=webhook_payload)
            
            if resp.status_code == 200:
                logger.info(f"✅ [SUCESSO] Webhook aceito! (Job: {job_id})")
                return 
            
            logger.warning(f"⚠️ [FALHA WEBHOOK] Status: {resp.status_code} - Body: {resp.text}")
            
        except Exception as e:
            logger.error(f"❌ [ERRO CONEXÃO] {e}")

        # TENTATIVA 2: Fallback (PUT direto na sessão)
        # Só faz sentido se tivermos dados válidos (não for erro)
        if status == "done":
            fallback_url = f"{base_url}/session/project/{project_id}/report"
            logger.info(f"🔄 [FALLBACK] Tentando salvar direto em: {fallback_url}")
            try:
                # O endpoint PUT espera { "report_data": { ... } }
                resp = await client.put(fallback_url, json={"report_data": report_data})
                if resp.status_code == 200:
                    logger.info("✅ [SALVO VIA PUT] Fallback funcionou.")
                else:
                    logger.error(f"❌ [FALHA FALLBACK] Status: {resp.status_code}")
            except Exception as e:
                logger.error(f"❌ [ERRO FALLBACK] {e}")

# --- ENDPOINTS ---

@router.get("/")
def home():
    return {
        "status": "Mock MCP Online v2.3", 
        "target_backend": BACKEND_BASE_URL
    }

@router.post("/start")
async def start_analysis(payload: MCPStartPayload, background_tasks: BackgroundTasks):
    new_job_id = str(uuid.uuid4())
    
    logger.info(f"⚡ [START] Recebido para Project ID: {payload.project_id}")
    logger.info(f"📝 Tipo Análise: {payload.analysis_type}")

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
        "nome_projeto": payload.nome_projeto or "Projeto Sem Nome"
    }

# Roteamento duplo para garantir compatibilidade com prefixes
app.include_router(router, prefix="/api/v1/analysis") 
app.include_router(router, prefix="") 

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
