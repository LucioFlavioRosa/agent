import json
import uuid
import yaml
import time
import traceback
import enum
from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, Literal, List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware

# --- Módulos do projeto ---
from tools.job_store import RedisJobStore
from tools import commit_multiplas_branchs

# --- Classes e dependências ---
from agents.agente_revisor import AgenteRevisor
from agents.agente_processador import AgenteProcessador
from tools.requisicao_openai import OpenAILLMProvider
from tools.requisicao_claude import AnthropicClaudeProvider
from tools.rag_retriever import AzureAISearchRAGRetriever
from tools.preenchimento import ChangesetFiller
from tools.github_reader import GitHubRepositoryReader
from domain.interfaces.llm_provider_interface import ILLMProvider
from tools.github_connector import GitHubConnector

# --- WORKFLOW_REGISTRY ---
def load_workflow_registry(filepath: str) -> dict:
    print(f"Carregando workflows do arquivo: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
WORKFLOW_REGISTRY = load_workflow_registry("workflows.yaml")
valid_analysis_keys = {key: key for key in WORKFLOW_REGISTRY.keys()}
ValidAnalysisTypes = enum.Enum('ValidAnalysisTypes', valid_analysis_keys)

# --- Modelos de Dados Pydantic ---
class StartAnalysisPayload(BaseModel):
    repo_name: str
    analysis_type: ValidAnalysisTypes
    branch_name: Optional[str] = None
    instrucoes_extras: Optional[str] = None
    usar_rag: bool = Field(False)
    gerar_relatorio_apenas: bool = Field(False)
    model_name: Optional[str] = Field(None, description="Nome do modelo de LLM a ser usado. Se nulo, usa o padrão.")

class StartAnalysisResponse(BaseModel):
    job_id: str

class UpdateJobPayload(BaseModel):
    job_id: str
    action: Literal["approve", "reject"]
    observacoes: Optional[str] = None

class PullRequestSummary(BaseModel):
    pull_request_url: str
    branch_name: str
    arquivos_modificados: List[str]

class FinalStatusResponse(BaseModel):
    job_id: str
    status: str
    summary: Optional[List[PullRequestSummary]] = Field(None)
    error_details: Optional[str] = Field(None)
    analysis_report: Optional[str] = Field(None)
    diagnostic_logs: Optional[Dict[str, Any]] = Field(None)

class ReportResponse(BaseModel):
    job_id: str
    analysis_report: Optional[str]

# --- Configuração do Servidor FastAPI ---
app = FastAPI(
    title="MCP Server - Multi-Agent Code Platform",
    description="Servidor robusto com Redis para orquestrar agentes de IA.",
    version="9.0.0" 
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
job_store = RedisJobStore()

def create_llm_provider(model_name: Optional[str], rag_retriever: AzureAISearchRAGRetriever) -> ILLMProvider:
    model_lower = (model_name or "").lower()
    if "claude" in model_lower:
        return AnthropicClaudeProvider(rag_retriever=rag_retriever)
    else:
        return OpenAILLMProvider(rag_retriever=rag_retriever)

# --- Funções de Tarefa (Tasks) ---
def handle_task_exception(job_id: str, e: Exception, step: str):
    error_message = f"Erro fatal durante a etapa '{step}': {str(e)}"
    print(f"[{job_id}] {error_message}")
    try:
        job_info = job_store.get_job(job_id)
        if job_info:
            job_info['status'] = 'failed'
            job_info['error_details'] = error_message
            job_store.set_job(job_id, job_info)
    except Exception as redis_e:
        print(f"[{job_id}] ERRO CRÍTICO ADICIONAL: Falha ao registrar o erro no Redis. Erro: {redis_e}")

def run_report_generation_task(job_id: str, payload: StartAnalysisPayload):
    # ... (sem alteração para esta etapa)
    pass

def run_workflow_task(job_id: str):
    job_info = None
    try:
        job_info = job_store.get_job(job_id)
        if not job_info: raise ValueError("Job não encontrado.")
        rag_retriever = AzureAISearchRAGRetriever()
        changeset_filler = ChangesetFiller()
        repo_reader = GitHubRepositoryReader()
        workflow = WORKFLOW_REGISTRY.get(job_info['data']['original_analysis_type'])
        if not workflow: raise ValueError("Workflow não encontrado.")
        previous_step_result = job_info['data'].get('step_0_result', {})
        resultado_refatoracao_etapa = {}
        resultado_agrupamento_etapa = {}
        etapas_do_workflow = workflow.get('steps', [])[1:]
        for i, step in enumerate(etapas_do_workflow):
            job_info['status'] = step['status_update']
            job_store.set_job(job_id, job_info)
            print(f"[{job_id}] ... Executando passo do workflow: {job_info['status']}")
            model_para_etapa = step.get('model_name', job_info.get('data', {}).get('model_name'))
            llm_provider = create_llm_provider(model_para_etapa, rag_retriever)
            agent_params = step.get('params', {}).copy()
            agent_params['usar_rag'] = job_info.get("data", {}).get("usar_rag", False)
            agent_params['model_name'] = model_para_etapa
            agent_type = step.get("agent_type", "processador")
            if agent_type == "revisor":
                agente = AgenteRevisor(repository_reader=repo_reader, llm_provider=llm_provider)
                agent_params.update({
                    'repositorio': job_info['data']['repo_name'],
                    'nome_branch': job_info['data']['branch_name'],
                    'instrucoes_extras': job_info['data']['analysis_report']
                })
                agent_response = agente.main(**agent_params)
            else:
                agente = AgenteProcessador(llm_provider=llm_provider)
                agent_params['codigo'] = previous_step_result
                agent_response = agente.main(**agent_params)
            json_string = agent_response['resultado']['reposta_final'].get('reposta_final', '')
            if not json_string.strip(): raise ValueError(f"IA retornou resposta vazia na etapa '{job_info['status']}'.")
            current_step_result = json.loads(json_string.replace("", "").replace("", "").strip())
            if i == 0:
                resultado_refatoracao_etapa = current_step_result
            if i == len(etapas_do_workflow) - 1:
                 resultado_agrupamento_etapa = current_step_result
            previous_step_result = current_step_result
        job_info['data']['resultado_refatoracao'] = resultado_refatoracao_etapa
        job_info['data']['resultado_agrupamento'] = resultado_agrupamento_etapa
        job_info['data']['diagnostic_logs'] = {
            "1_json_refatoracao_inicial": resultado_refatoracao_etapa,
            "2_json_agrupamento_recebido": resultado_agrupamento_etapa
        }
        job_info['status'] = 'populating_data'
        job_store.set_job(job_id, job_info)
        dados_preenchidos = changeset_filler.main(
            json_agrupado=resultado_agrupamento_etapa,
            json_inicial=resultado_refatoracao_etapa
        )
        dados_finais_formatados = {"resumo_geral": dados_preenchidos.get("resumo_geral", ""), "grupos": []}
        for nome_grupo, detalhes_pr in dados_preenchidos.items():
            if nome_grupo == "resumo_geral": continue
            dados_finais_formatados["grupos"].append({"branch_sugerida": nome_grupo, "titulo_pr": detalhes_pr.get("resumo_do_pr", ""), "resumo_do_pr": detalhes_pr.get("descricao_do_pr", ""), "conjunto_de_mudancas": detalhes_pr.get("conjunto_de_mudancas", [])})
        job_info['status'] = 'committing_to_github'
        job_store.set_job(job_id, job_info)
        # --- INTEGRAÇÃO DA LÓGICA DE COMMIT DIRETO NA MAIN ---
        repo_name = job_info['data']['repo_name']
        repo_obj, repo_metadata = GitHubConnector.connection(repo_name, return_info=True)
        is_novo_repo = repo_metadata.get('is_novo_repo', False)
        commit_direto_main = is_novo_repo
        commit_results = commit_multiplas_branchs.processar_e_subir_mudancas_agrupadas(
            nome_repo=repo_name, 
            dados_agrupados=dados_finais_formatados,
            commit_direto_main=commit_direto_main
        )
        job_info['data']['commit_details'] = commit_results
        job_info['status'] = 'completed'
        job_store.set_job(job_id, job_info)
        print(f"[{job_id}] Processo concluído com sucesso!")
    except Exception as e:
        traceback.print_exc()
        handle_task_exception(job_id, e, job_info.get('status', 'workflow') if job_info else 'workflow')
# ... (restante do arquivo permanece inalterado)
