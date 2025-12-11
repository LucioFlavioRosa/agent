import logging
import uuid
import os
import asyncio
import httpx
import json # Importação necessária para o json.loads
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
# Importe o enriquecimento se estiver usando
from config.analysis_context_enrichment import ContextEnrichmentService # Ajuste o caminho se necessário

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure.monitor.opentelemetry.exporter").setLevel(logging.WARNING)
logger = logging.getLogger("MockMCP")

app = FastAPI(title="MCP Mock Service", version="2.3.1 - Bugfix Scope")
router = APIRouter()

BACKEND_BASE_URL = os.environ.get("TARGET_BACKEND_URL", "http://localhost:8000")
project_tracker = ProjectTracker()

@router.get("/")
def home():
    return {
        "status": "Mock MCP Online v2.3.1", 
        "target_backend": BACKEND_BASE_URL
    }

@router.post("/start")
async def start_analysis(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    # 1. Correção de Chaves (Retrocompatibilidade)
    instrucoes = payload.get("instrucoes_extras") or payload.get("comentario_extra")
    if instrucoes:
        payload["instrucoes_extras"] = instrucoes
        payload["comentario_extra"] = instrucoes
    
    logger.info(f"📥 [PAYLOAD RECEBIDO]: {payload}")

    # 2. Parsing do Modelo (Sem duplicidade)
    try:
        mcp_request = MCPRequest(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Payload inválido: {e}")
    
    # 3. Carregar Configuração
    try:
        task_config = load_task_config(mcp_request.analysis_type)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Configuração não encontrada: {e}")

    # 4. Enriquecimento de Contexto (Opcional - mas recomendado se estiver usando refinamento)
    if getattr(task_config, 'context_enrichment', False):
        try:
            # Importante: Passar usuario e nome_projeto para achar o blob correto
            enriched_text = await ContextEnrichmentService.enrich_instructions(
                project_id=mcp_request.project_id,
                analysis_type=mcp_request.analysis_type,
                instrucoes_extras=mcp_request.instrucoes_extras,
                usuario_executor=mcp_request.usuario_executor,
                nome_projeto=mcp_request.nome_projeto
            )
            mcp_request.instrucoes_extras = enriched_text
        except Exception as e:
            logger.warning(f"⚠️ Falha no enriquecimento de contexto: {e}")

    # 5. Carregar Prompt
    try:
        instrucoes_padrao = load_prompt_instructions(f"{task_config.instrucoes_extras}.md")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Prompt markdown não encontrado: {e}")

    llm_request_params = LLMRequestBuilder.build_request(
        mcp_request,
        task_config,
        instrucoes_padrao
    )

    logger.info(f"🚀 [REQ. PROCESSADA PARA O MCP]: {llm_request_params}")
    
    # 6. Definição segura de Variáveis para Background Task
    project_id = mcp_request.project_id
    
    # Tenta pegar job_id do request, se não existir, usa o project_id
    # Isso evita o erro caso seu modelo MCPRequest não tenha o campo job_id
    job_id = getattr(mcp_request, 'job_id', project_id)

    project_tracker.set_status(project_id, 'processing')
    
    # Passamos APENAS tipos primitivos ou dicts para a task, nunca o objeto mcp_request complexo
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
    # ATENÇÃO: A variável 'mcp_request' NÃO EXISTE aqui dentro. 
    # Use apenas 'project_id', 'job_id' ou 'llm_request_params'.
    
    try:
        orchestrator = LLMOrchestrator()
        agent_result = orchestrator.execute_analysis(llm_request_params)
        
        # Extração segura da resposta da LLM
        # Dependendo do seu Orchestrator, a estrutura pode variar. Ajuste se necessário.
        if isinstance(agent_result, dict) and 'resultado' in agent_result:
             # Tenta navegar na estrutura comum do seu orchestrator
             raw_content = agent_result.get('resultado', {}).get('reposta_final', agent_result)
             if isinstance(raw_content, dict) and 'reposta_final' in raw_content:
                 raw_content = raw_content['reposta_final']
        else:
             raw_content = agent_result

        # Limpeza
        cleaned_result = clean_llm_response(raw_content)
        
        # Garantia de Dicionário
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

        # Correção para Erro 422 (Chave Única)
        if len(final_report_data.keys()) > 1:
            final_report_data = {"relatorio_consolidado": final_report_data}
        elif len(final_report_data.keys()) == 0:
            final_report_data = {"error": "JSON vazio retornado pela LLM"}

        # Atualiza Tracker
        project_tracker.set_status(project_id, 'done')
        project_tracker.set_result(project_id, final_report_data)

        # Prepara Webhook
        webhook_payload = {
            "project_id": project_id,
            "job_id": job_id, # Usa a variável local job_id
            "status": "done",
            "report_data": final_report_data,
            "analysis_type": llm_request_params.get("analysis_type")
        }

        # Envio
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
            
            # Fallback PUT
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

app.include_router(router, prefix="/api/v1/analysis")
app.include_router(router, prefix="")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
