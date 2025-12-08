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

app = FastAPI(title="MCP Mock Service", version="2.2.0 - Strict Spec Compliance")
router = APIRouter()

# URL do Backend Principal
BACKEND_BASE_URL = os.environ.get("TARGET_BACKEND_URL", "http://localhost:8000")

# --- MODELOS AJUSTADOS (CRÍTICO) ---
class MCPStartPayload(BaseModel):
    # 1. Ajustado para bater com a doc: 'project_id' é o identificador principal
    project_id: str 
    
    # 2. Ajustado: 'analysis_type' se mantém
    analysis_type: str
    
    # 3. CORREÇÃO: O backend envia 'instrucoes_extras', não 'comentario_usuario'
    instrucoes_extras: Optional[str] = None 
    
    # 4. Ajustado: 'arquivo_docx' (texto extraído)
    arquivo_docx: Optional[str] = None
    
    # 5. CORREÇÃO: O backend envia 'nome_projeto', e não 'projeto'. 
    # Deixei opcional pois o ID é o que importa.
    nome_projeto: Optional[str] = None 

    # Campos que não estão na doc oficial de envio devem ser removidos ou opcionais
    usuario_executor: Optional[str] = None

# --- DADOS MOCKADOS (Mantidos) ---
DATA_EPICOS = {
    "epicos_report": [
        { "id": 1, "titulo": "Autenticação e Segurança", "descricao": "Implementar login via Azure AD.", "prioridade": "Alta" },
        { "id": 2, "titulo": "Processamento de Documentos", "descricao": "Upload e extração de texto.", "prioridade": "Alta" }
    ]
}

DATA_EPICOS_REFINAMENTO = {
    "epicos_report": [
        { "id": 1, "titulo": "Autenticação e Segurança para a primeira fase", 
         "descricao": "Implementar login via Azure AD sem ser multi tenant.", "prioridade": "Alta" },
        { "id": 2, "titulo": "Processamento de Documentos", "descricao": "Upload e extração de texto.", "prioridade": "Alta" }
    ]
}

DATA_FEATURES = {
    "features_report": [
        {"id": 101, "epico_id": 1, "nome": "Configurar App Registration Azure", "descricao": "Criar app no entra ID"},
        {"id": 102, "epico_id": 1, "nome": "Middleware de Validação JWT", "descricao": "Validar token no backend Python"}
    ]
}

DATA_FEATURES_REFINAMENTO = {
    "features_report": [
        {"id": 101, "epico_id": 1, "nome": "Configurar App Registration Azure", 
         "descricao": "Criar app no entra ID",
        "critério_de_aceite": "eu tenho que conseguir registrar usuários externos"},
        {"id": 102, "epico_id": 1, "nome": "Middleware de Validação JWT", 
         "descricao": "Validar token no backend Python"}
    ]
}

DATA_RISCOS = {
    "premissas_riscos_report": [
        {"id": 1, "tipo": "Risco", "descricao": "Latência alta na comunicação."},
        {"id": 2, "tipo": "Premissa", "descricao": "Redis disponível na VNET."}
    ]
}

# --- LÓGICA DE ENVIO ---
async def process_and_send_webhook(job_id: str, project_id: str, analysis_type: str):
    logger.info(f"⏳ [MOCK] Processando Job {job_id} para Projeto {project_id} ({analysis_type})...")
    
    # Simula latência
    await asyncio.sleep(5) 
    
    # Lógica simples para decidir sucesso ou erro (pode criar um header especial para forçar erro se quiser)
    status = "done"
    report_data = {}
    error_payload = {}

    if "erro_teste" in analysis_type:
        status = "error"
        error_payload = {
            "error_type": "simulation_error",
            "error_message": "Erro simulado pelo Mock MCP para teste de resiliência."
        }
    else:
        # Seleção de Payload
        if "criacao_features_azure_devops" in analysis_type:
            report_data = DATA_FEATURES
        elif "refinamento_features_azure_devops" in analysis_type:
            report_data = DATA_FEATURES_REFINAMENTO
        elif "criacao_epicos_azure_devops" in analysis_type:
            report_data = DATA_EPICOS
        elif "refinamento_epicos_azure_devops" in analysis_type:
            report_data = DATA_EPICOS_REFINAMENTO
        elif "riscos" in analysis_type or "tech_debt" in analysis_type:
            report_data = DATA_RISCOS
        

    # PREPARAÇÃO DO PAYLOAD (Conforme Doc 2.1)
    webhook_payload = {
        "job_id": job_id,
        "project_id": project_id,
        "status": status,
    }

    if status == "done":
        webhook_payload["report_data"] = report_data
    elif status == "error":
        webhook_payload.update(error_payload)

    async with httpx.AsyncClient(timeout=30.0) as client:
        base_url = BACKEND_BASE_URL.rstrip('/')
        webhook_url = f"{base_url}/webhooks/mcp"
        
        logger.info(f"📤 [WEBHOOK] Enviando {status} para {webhook_url}")
        
        try:
            # TENTATIVA 1: Webhook Padrão
            resp = await client.post(webhook_url, json=webhook_payload)
            
            if resp.status_code == 200:
                logger.info(f"✅ [SUCESSO] Webhook aceito! (Job: {job_id})")
                return 
            
            logger.warning(f"⚠️ [FALHA WEBHOOK] Status: {resp.status_code} - Body: {resp.text}")
            
        except Exception as e:
            logger.error(f"❌ [ERRO CONEXÃO] {e}")

        # TENTATIVA 2: Fallback (Apenas se for sucesso, pois endpoint de report não aceita erro)
        if status == "done":
            fallback_url = f"{base_url}/session/project/{project_id}/report"
            logger.info(f"🔄 [FALLBACK] Tentando: {fallback_url}")
            try:
                # Nota: A doc diz que esse endpoint espera { "report_data": ... } no corpo? 
                # Se for PUT direto, verifique se o wrapper report_data é necessário.
                # Baseado na doc 1.5: { "report_data": { ... } } -> Correto.
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
        "status": "Mock MCP Online v2.2", 
        "routes": ["/start", "/api/v1/analysis/start"],
        "target_backend": BACKEND_BASE_URL
    }

@router.post("/start")
async def start_analysis(payload: MCPStartPayload, background_tasks: BackgroundTasks):
    new_job_id = str(uuid.uuid4())
    
    logger.info(f"⚡ [START] Recebido para Project ID: {payload.project_id}")
    # Uso correto do campo instrucoes_extras
    logger.info(f"📝 Instruções: {payload.instrucoes_extras or 'Nenhuma'}")

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

# Roteamento duplo para garantir compatibilidade
app.include_router(router, prefix="/api/v1/analysis") 
app.include_router(router, prefix="") 

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
