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

app = FastAPI(title="MCP Mock Service", version="1.1.0 - Logic Fix")
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

# --- DADOS MOCKADOS ---
# --- DADOS MOCKADOS (CORRIGIDOS) ---
DATA_CRIACAO = {
    "epicos":{
    "epicos_report": [
        {
            "id": 1, 
            "titulo": "Autenticação Azure AD", 
            "descricao": "Implementar login seguro com OAuth2. Vou testar Algumas coisas", 
            "tempo estimado": "2 sprint", 
            "criterios de aceite": "eu preciso fazer esse login de qualquer maquina"
        },
        {
            "id": 2, 
            "titulo": "Processamento de Arquivos", 
            "descricao": "Ler e extrair texto de DOCX."
        },
        {
            "id": 3, 
            "titulo": "Dashboard de Métricas", 
            "descricao": "Visualizar status dos projetos."
        }
    ]
}
}

DATA_REFINAMENTO = {
    # Removida a chave externa "epicos"
    "epicos_report": [
        {"id": 1, "titulo": "Autenticação Azure AD com maior atençao", "descricao": "Implementar login seguro com OAuth2. NONO"},
        {"id": 2, "titulo": "Processamento de Arquivos refinados", "descricao": "Ler e extrair texto de DOCX. NONO"},
        {"id": 3, "titulo": "Dashboard de Métricas refinados", "descricao": "Visualizar status dos projetos. NONO"}
    ]
}

FEATURE_CRIACAO = {
    # Removida a chave externa "features". Agora "features_report" é a raiz.
    "features_report": [
        {"feature id": 1, "epico id ": "1", "titulo": "setup infra na nuvem", "prazo": "2 dias"},
        {"feature id": 2, "epico id ": "2", "titulo": "testes de segurança", "prazo": "1 dia"}
    ]
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
    
    elif analysis_type == "criacao_features_azure_devops":
        logger.info("👉 Selecionando dados de FEATURES")
        report_data = FEATURE_CRIACAO
        report_type = "features" 
        
    else:
        logger.info("👉 Selecionando dados de CRIAÇÃO (Default)")
        report_data = DATA_CRIACAO
        report_type = "epicos"

    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"Content-Type": "application/json"}
        base_url = BACKEND_BASE_URL.rstrip('/')

        # AQUI O SESSION_ID É O QUE VEIO DO PAYLOAD ORIGINAL
        webhook_payload = {
            "session_id": session_id,
            "job_id": job_id,
            "status": "done",
            "report_type": report_type,
            "report_data": report_data
        }
        
        logger.info(f"📤 [WEBHOOK] Tentando enviar para {base_url}/webhooks/mcp | Session: {session_id}")
        
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

        # TENTATIVA 2: Fallback (Usa o mesmo session_id)
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
    return {"status": "Mock MCP Online v1.1.0", "target": BACKEND_BASE_URL}

@router.post("/start")
async def start_analysis_mock(payload: FakeMCPStartPayload, background_tasks: BackgroundTasks):
    """
    Garante que o session_id de entrada é EXATAMENTE o de saída e uso interno.
    """
    
    # Se o payload não trouxer session_id, usamos 'None' ou uma string vazia, 
    # mas NÃO geramos um novo para respeitar a regra de "exclusivamente entrada".
    input_session_id = payload.session_id

    # Usamos o próprio session_id como job_id para rastreio no log, 
    # ou 'unknown' se vier nulo, apenas para não quebrar o print.
    job_id_ref = input_session_id if input_session_id else "no-id-provided"
    
    logger.info(f"⚡ [MOCK] Start recebido. Sessão INPUT: {input_session_id}")

    # CORREÇÃO CRÍTICA AQUI:
    # Passamos os argumentos nomeados para garantir que cada valor vá para o lugar certo.
    # Antes, 'payload.analysis_type' estava caindo no lugar do 'session_id' na função async.
    background_tasks.add_task(
        send_result_to_backend, 
        job_id=job_id_ref,           # 1º argumento da função
        session_id=input_session_id, # 2º argumento (GARANTIDO SER O INPUT)
        analysis_type=payload.analysis_type # 3º argumento
    )

    # Retorno imediato
    return {
        "session_id": input_session_id, # Retorna estritamente o que entrou
        "status": "queued",
        "message": "Análise iniciada. Mock responderá em breve."
    }

app.include_router(router, prefix="/fake-mcp/api/v1/analysis")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
