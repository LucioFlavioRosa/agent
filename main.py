import logging
import uuid
import os
import asyncio
import httpx
from fastapi import FastAPI, APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from models.mcp_request import MCPRequest
from services.config_loader import load_task_config
from services.prompt_loader import load_prompt_instructions
from services.llm_request_builder import LLMRequestBuilder
from services.llm_orchestrator import LLMOrchestrator
from services.response_cleaner import clean_llm_response
from services.project_tracker import ProjectTracker

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure.monitor.opentelemetry.exporter").setLevel(logging.WARNING)
logger = logging.getLogger("MockMCP")



app = FastAPI(title="MCP Mock Service", version="2.3.0 - MCP Dinâmico")
router = APIRouter()

BACKEND_BASE_URL = os.environ.get("TARGET_BACKEND_URL", "http://localhost:8000")
project_tracker = ProjectTracker()

DATA_EPICOS =  {"epicos_report": [
        { "id": 1, "titulo": "Autenticação e Segurança", "descricao": "Implementar login via Azure AD.", "prioridade": "Alta" },
        { "id": 2, "titulo": "Processamento de Documentos", "descricao": "Upload e extração de texto.", "prioridade": "Alta" }
    ]
               }

@router.get("/")
def home():
    return {
        "status": "Mock MCP Online v2.3", 
        "target_backend": BACKEND_BASE_URL
    }

@router.post("/start")
async def start_analysis(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    logger.info(f"📥 [PAYLOAD RECEBIDO]: {payload}")

    try:
        mcp_request = MCPRequest(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Payload inválido: {e}")
            
    try:
        mcp_request = MCPRequest(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Payload inválido: {e}")
    try:
        task_config = load_task_config(mcp_request.analysis_type)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Configuração não encontrada para analysis_type: {e}")
    try:
        instrucoes_padrao = load_prompt_instructions(f"{task_config.instrucoes_extras}.md")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Prompt markdown não encontrado: {e}")
    llm_request_params = LLMRequestBuilder.build_request(
        mcp_request,
        task_config,
        instrucoes_padrao
    )
    # --- ADICIONE ESTA LINHA AQUI ---
    logger.info(f"🚀 [REQ. PROCESSADA PARA O MCP]: {llm_request_params}")
    # --------------------------------
    project_id = mcp_request.project_id
    project_tracker.set_status(project_id, 'processing')
    background_tasks.add_task(
        process_analysis_task,
        project_id,
        llm_request_params
    )
    return {
        "message": "Análise solicitada com sucesso ao agente MCP dinâmico.",
        "project_id": project_id,
        "status": "processing"
    }

async def process_analysis_task(project_id: str, llm_request_params: Dict[str, Any]):
    try:
        orchestrator = LLMOrchestrator()
        agent_result = orchestrator.execute_analysis(llm_request_params)
        logger.info(f"🤖 [RAW LLM RESPONSE - ANTES DA LIMPEZA]: {agent_result}")
        cleaned_result = clean_llm_response(agent_result)
        project_tracker.set_status(project_id, 'done')
        project_tracker.set_result(project_id, cleaned_result)
        webhook_payload = {
            "project_id": project_id,
            "status": "done",
            "report_data": cleaned_result,
            "analysis_type": llm_request_params.get("analysis_type")
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = BACKEND_BASE_URL.rstrip('/')
            webhook_url = f"{base_url}/webhooks/mcp"
            try:
                resp = await client.post(webhook_url, json=webhook_payload)
                if resp.status_code == 200:
                    logger.info(f"✅ [SUCESSO] Webhook aceito! (Project: {project_id})")
                    return
                logger.warning(f"⚠️ [FALHA WEBHOOK] Status: {resp.status_code} - Body: {resp.text}")
            except Exception as e:
                logger.error(f"❌ [ERRO CONEXÃO] {e}")
            fallback_url = f"{base_url}/session/project/{project_id}/report"
            try:
                resp = await client.put(fallback_url, json={"report_data": cleaned_result})
                if resp.status_code == 200:
                    logger.info("✅ [SALVO VIA PUT] Fallback funcionou.")
                else:
                    logger.error(f"❌ [FALHA FALLBACK] Status: {resp.status_code}")
            except Exception as e:
                logger.error(f"❌ [ERRO FALLBACK] {e}")
    except Exception as e:
        logger.error(f"❌ [ERRO MCP FLOW] {e}")
        project_tracker.set_status(project_id, 'error')
        project_tracker.set_result(project_id, str(e))
        webhook_payload = {
            "project_id": project_id,
            "status": "error",
            "error_message": str(e),
            "analysis_type": llm_request_params.get("analysis_type")
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = BACKEND_BASE_URL.rstrip('/')
            webhook_url = f"{base_url}/webhooks/mcp"
            try:
                await client.post(webhook_url, json=webhook_payload)
            except Exception as e2:
                logger.error(f"❌ [ERRO CONEXÃO ERROR WEBHOOK] {e2}")

@router.get("/status/{project_id}")
def get_project_status(project_id: str):
    status = project_tracker.get_status(project_id)
    result = project_tracker.get_result(project_id)
    return {
        "project_id": project_id,
        "status": status,
        "result": result
    }

app.include_router(router, prefix="/api/v1/analysis")
app.include_router(router, prefix="")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
