import logging
import uuid
import os
import asyncio
import httpx
import json
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

app = FastAPI(title="MCP Mock Service", version="2.4.1 - Debug Logging")
router = APIRouter()

BACKEND_BASE_URL = os.environ.get("TARGET_BACKEND_URL", "http://localhost:8000")
project_tracker = ProjectTracker()

import re
import json

def extrair_conteudo_json(dados):
    """
    1. Varre recursivamente o dicionário/lista buscando uma string que contenha ```json
    2. Extrai o conteúdo dentro do bloco de código
    3. Retorna o objeto JSON (dict) pronto
    """
    
    # Função interna para encontrar a string crua (o texto do LLM)
    def encontrar_string_com_markdown(obj):
        if isinstance(obj, str):
            if "```json" in obj:
                return obj
        elif isinstance(obj, dict):
            for value in obj.values():
                resultado = encontrar_string_com_markdown(value)
                if resultado: return resultado
        elif isinstance(obj, list):
            for item in obj:
                resultado = encontrar_string_com_markdown(item)
                if resultado: return resultado
        return None

    # 1. Acha a string que tem o markdown
    texto_bruto = encontrar_string_com_markdown(dados)
    
    if not texto_bruto:
        # Se não achou markdown, tenta ver se o próprio input já é o dict alvo
        # ou retorna erro/vazio dependendo da sua regra de negócio
        return dados 

    # 2. Usa Regex para pegar TUDO que está entre ```json e ```
    # O re.DOTALL faz o ponto (.) pegar quebras de linha também
    match = re.search(r"```json\s*(.*?)\s*```", texto_bruto, re.DOTALL | re.IGNORECASE)
    
    if match:
        json_str = match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"Erro ao decodificar JSON extraído: {e}")
            return None
    
    return None

@router.get("/")
def home():
    return {
        "status": "Mock MCP Online v2.4.1", 
        "target_backend": BACKEND_BASE_URL
    }

@router.post("/start")
async def start_analysis(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    instrucoes = payload.get("instrucoes_extras") or payload.get("comentario_extra")
    if instrucoes:
        payload["instrucoes_extras"] = instrucoes
        payload["comentario_extra"] = instrucoes

    logger.info("=" * 50)
    logger.info(f"📥 [PAYLOAD RECEBIDO]:\n{json.dumps(payload, indent=2, default=str)}")
    logger.info("=" * 50)
    
    logger.info(f"📥 [START] Recebido para Project ID: {payload.get('project_id')} | Job ID: {payload.get('job_id')}")
    try:
        mcp_request = MCPRequest(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Payload inválido: {e}")
    try:
        task_config = load_task_config(mcp_request.analysis_type)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Configuração não encontrada: {e}")
    try:
        instrucoes_padrao = load_prompt_instructions(f"{task_config.instrucoes_extras}.md")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Prompt markdown não encontrado: {e}")
    llm_request_params = LLMRequestBuilder.build_request(
        mcp_request,
        task_config,
        instrucoes_padrao
    )
    project_id = mcp_request.project_id
    job_id = mcp_request.job_id if mcp_request.job_id else str(uuid.uuid4())
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
    try:
        orchestrator = LLMOrchestrator()
        llm_request_params["job_id"] = job_id
        agent_result = orchestrator.execute_analysis(llm_request_params)
        raw_content = extrair_conteudo_json(agent_result)
        cleaned_result = clean_llm_response(raw_content)
        logger.info(f"📤 [RESPOSTA lIMPA] Payload:\n{json.dumps(cleaned_result, indent=2, default=str)}")
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
        if len(final_report_data.keys()) > 1:
            final_report_data = {"relatorio_consolidado": final_report_data}
        elif len(final_report_data.keys()) == 0:
            final_report_data = {"error": "JSON vazio retornado pela LLM"}
        project_tracker.set_status(project_id, 'done')
        project_tracker.set_result(project_id, final_report_data)
        webhook_payload = {
            "project_id": project_id,
            "job_id": job_id,
            "status": "done",
            "report_data": final_report_data,
            "analysis_type": llm_request_params.get("analysis_type")
        }
        logger.info(f"📤 [ENVIANDO WEBHOOK] Payload:\n{json.dumps(webhook_payload, indent=2, default=str)}")
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
            fallback_url = f"{base_url}/session/project/{project_id}/report"
            try:
                await client.put(fallback_url, json={"report_data": final_report_data})
            except Exception as e:
                logger.error(f"❌ [ERRO FALLBACK] {e}")
    except Exception as e:
        logger.error(f"❌ [ERRO MCP FLOW] {e}")
        project_tracker.set_status(project_id, 'error')
        project_tracker.set_result(project_id, str(e))
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
