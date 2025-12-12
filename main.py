import logging
import uuid
import os
import asyncio
import httpx
import json
from fastapi import FastAPI, APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

# Imports de serviços internos do MCP
from models.mcp_request import MCPRequest
from services.config_loader import load_task_config
from services.prompt_loader import load_prompt_instructions
from services.llm_request_builder import LLMRequestBuilder
from services.llm_orchestrator import LLMOrchestrator
from services.response_cleaner import clean_llm_response
from services.project_tracker import ProjectTracker

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure.monitor.opentelemetry.exporter").setLevel(logging.WARNING)
logger = logging.getLogger("MockMCP")

app = FastAPI(title="MCP Mock Service", version="2.4.1 - Debug Logging")
router = APIRouter()

BACKEND_BASE_URL = os.environ.get("TARGET_BACKEND_URL", "http://localhost:8000")
project_tracker = ProjectTracker()

@router.get("/")
def home():
    return {
        "status": "Mock MCP Online v2.4.1", 
        "target_backend": BACKEND_BASE_URL
    }

@router.post("/start")
async def start_analysis(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    # 1. Correção de Chaves
    instrucoes = payload.get("instrucoes_extras") or payload.get("comentario_extra")
    if instrucoes:
        payload["instrucoes_extras"] = instrucoes
        payload["comentario_extra"] = instrucoes
    
    # Log de entrada mantido (importante para debug inicial)
    logger.info(f"📥 [START] Recebido para Project ID: {payload.get('project_id')} | Job ID: {payload.get('job_id')}")

    # 2. Parsing
    try:
        mcp_request = MCPRequest(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Payload inválido: {e}")
    
    # 3. Configuração
    try:
        task_config = load_task_config(mcp_request.analysis_type)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Configuração não encontrada: {e}")

    # 5. Prompt
    try:
        instrucoes_padrao = load_prompt_instructions(f"{task_config.instrucoes_extras}.md")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Prompt markdown não encontrado: {e}")

    # 6. Builder
    llm_request_params = LLMRequestBuilder.build_request(
        mcp_request,
        task_config,
        instrucoes_padrao
    )

    # 7. Background Task
    project_id = mcp_request.project_id
    # Garante que job_id existe (usa project_id como fallback se vier vazio)
    job_id = getattr(mcp_request, 'job_id', project_id)

    project_tracker.set_status(project_id, 'processing')
    
    background_tasks.add_task(
        process_analysis_task,
        project_id,
        job_id,
        llm_request_params
    )

    return {
        "message": "Análise solicitada com sucesso.",
        "project_id": project_id,
        "job_id": job_id,   
        "status": "processing"
    }

async def process_analysis_task(project_id: str, job_id: str, llm_request_params: Dict[str, Any]):
    """
    Executa a chamada da LLM, limpa o JSON e envia o Webhook de volta para o Backend.
    """
    try:
        orchestrator = LLMOrchestrator()
        agent_result = orchestrator.execute_analysis(llm_request_params)
        
        # Extração de resposta
        if isinstance(agent_result, dict) and 'resultado' in agent_result:
             raw_content = agent_result.get('resultado', {}).get('reposta_final', agent_result)
             if isinstance(raw_content, dict) and 'reposta_final' in raw_content:
                 raw_content = raw_content['reposta_final']
        else:
             raw_content = agent_result

        # Limpeza
        cleaned_result = clean_llm_response(raw_content)
        
        # Garantia de JSON
        final_report_data = {}
        if isinstance(cleaned_result, str):
            try:
                final_report_data = json.loads(cleaned_result)
            except:
                final_report_data = {"error": "Falha no parse JSON", "raw": str(cleaned_result)[:200]}
        elif isinstance(cleaned_result, dict):
            final_report_data = cleaned_result
        else:
             final_report_data = {"error": "Tipo de retorno desconhecido"}

        # Correção Erro 422
        if len(final_report_data.keys()) > 1:
            final_report_data = {"relatorio_consolidado": final_report_data}
        elif len(final_report_data.keys()) == 0:
            final_report_data = {"error": "JSON vazio retornado pela LLM"}

        # Atualiza Tracker
        project_tracker.set_status(project_id, 'done')
        project_tracker.set_result(project_id, final_report_data)

        # Monta Payload
        webhook_payload = {
            "project_id": project_id,
            "job_id": job_id,
            "status": "done",
            "report_data": final_report_data,
            "analysis_type": llm_request_params.get("analysis_type")
        }

        # --- LOG DETALHADO DO QUE ESTÁ SENDO ENVIADO ---
        # Aqui você verá exatamente se o job_id está correto antes de sair
        logger.info(f"📤 [ENVIANDO WEBHOOK] Payload:\n{json.dumps(webhook_payload, indent=2, default=str)}")
        # -----------------------------------------------

        # Envia Webhook
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = BACKEND_BASE_URL.rstrip('/')
            webhook_url = f"{base_url}/webhooks/mcp"
            
            try:
                resp = await client.post(webhook_url, json=webhook_payload)
                if resp.status_code == 200:
                    logger.info(f"✅ [SUCESSO] Webhook aceito pelo Backend! (Job: {job_id})")
                    return
                logger.warning(f"⚠️ [FALHA WEBHOOK] Status: {resp.status_code} - Body: {resp.text}")
            except Exception as e:
                logger.error(f"❌ [ERRO CONEXÃO] {e}")
            
            # Fallback
            fallback_url = f"{base_url}/session/project/{project_id}/report"
            try:
                await client.put(fallback_url, json={"report_data": final_report_data})
            except Exception as e:
                logger.error(f"❌ [ERRO FALLBACK] {e}")

    except Exception as e:
        logger.error(f"❌ [ERRO MCP FLOW] {e}")
        project_tracker.set_status(project_id, 'error')
        project_tracker.set_result(project_id, str(e))
        
        # Webhook de Erro
        webhook_payload = {
            "project_id": project_id,
            "job_id": job_id,
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
