import json
import uuid
import yaml
import time
import traceback
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


# --- Modelos de Dados Pydantic ---
class StartAnalysisPayload(BaseModel):
    repo_name: str
    analysis_type: Literal[
        "relatorio_cleancode", "relatorio_performance_eficiencia",
        "relatorio_simplicacao_debito_tecnico", "relatorio_solid", 
        "relatorio_conformidades", "relatorio_teste_unitario",
        "relatorio_owasp"
    ]
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
    """
    Analisa o nome do modelo e instancia a classe de provedor de LLM correta.
    Esta função é o ponto central para adicionar ou alterar provedores.
    """
    model_lower = (model_name or "").lower()
    
    if "claude" in model_lower:
        return AnthropicClaudeProvider(rag_retriever=rag_retriever)
    
    else:
        return OpenAILLMProvider(rag_retriever=rag_retriever)


# --- WORKFLOW_REGISTRY ---
def load_workflow_registry(filepath: str) -> dict:
    print(f"Carregando workflows do arquivo: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
WORKFLOW_REGISTRY = load_workflow_registry("workflows.yaml")


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
    job_info = None
    try:
        job_info = job_store.get_job(job_id)
        if not job_info: raise ValueError("Job não encontrado.")

        job_info['status'] = 'iniciando_a_analise'
        job_store.set_job(job_id, job_info)
        
        repo_reader = GitHubRepositoryReader()
        rag_retriever = AzureAISearchRAGRetriever()
        llm_provider = create_llm_provider(payload.model_name, rag_retriever)
        agente = AgenteRevisor(repository_reader=repo_reader, llm_provider=llm_provider)

        job_info['status'] = 'comecando_analise_llm'
        job_store.set_job(job_id, job_info)

        resposta_agente = agente.main(
            tipo_analise=payload.analysis_type,
            repositorio=payload.repo_name,
            nome_branch=payload.branch_name,
            instrucoes_extras=payload.instrucoes_extras,
            usar_rag=payload.usar_rag,
            model_name=payload.model_name
        )
        
        full_llm_response_obj = resposta_agente['resultado']['reposta_final']
        json_string_from_llm = full_llm_response_obj.get('reposta_final', '') # Usar .get para segurança

        if not json_string_from_llm or not json_string_from_llm.strip():
            raise ValueError("A resposta da IA (LLM) veio vazia. Isso pode ser causado por filtros de conteúdo da OpenAI ou um erro no modelo. O processo não pode continuar.")
        
        parsed_response = json.loads(json_string_from_llm.replace("```json", "").replace("```", "").strip())
        
        report_text = parsed_response.get("relatorio", "Relatório não fornecido pela IA.")

        job_info['data']['analysis_report'] = report_text
        
        if payload.gerar_relatorio_apenas:
            job_info['status'] = 'completed'
        else:
            job_info['status'] = 'pending_approval'

        job_store.set_job(job_id, job_info)

    except Exception as e:
        traceback.print_exc()
        # Passa a versão mais atual do job_info para o handler de exceção
        handle_task_exception(job_id, e, job_info.get('status', 'report_generation') if job_info else 'report_generation')


def run_workflow_task(job_id: str):
    job_info = None
    try:
        job_info = job_store.get_job(job_id)
        if not job_info: raise ValueError("Job não encontrado no início do workflow.")

        # --- MUDANÇA: Dependências genéricas são criadas aqui ---
        # As dependências específicas (provedor e agente) serão criadas dentro do loop.
        repo_reader = GitHubRepositoryReader()
        rag_retriever = AzureAISearchRAGRetriever()
        changeset_filler = ChangesetFiller()

        # --- LÓGICA DO WORKFLOW ---
        original_analysis_type = job_info['data']['original_analysis_type']
        workflow = WORKFLOW_REGISTRY.get(original_analysis_type)
        if not workflow: raise ValueError(f"Nenhum workflow definido para: {original_analysis_type}")

        previous_step_result = None

        for i, step in enumerate(workflow['steps']):
            job_info['status'] = step['status_update']
            job_store.set_job(job_id, job_info)
            print(f"[{job_id}] ... Executando passo: {job_info['status']}")

            model_para_etapa = step.get('model_name', job_info.get('data', {}).get('model_name'))
            
            # 2. Usa a fábrica para criar o provedor de LLM correto para a etapa.
            llm_provider = create_llm_provider(model_para_etapa, rag_retriever)
            
            # 3. Prepara os parâmetros comuns do agente.
            agent_params = step['params'].copy()
            agent_params['usar_rag'] = job_info.get("data", {}).get("usar_rag", False)
            agent_params['model_name'] = model_para_etapa # Passa o nome do modelo adiante
            
            # 4. Seleciona e instancia o tipo de agente correto para a tarefa.
            if i == 0:
                agente_para_etapa = AgenteRevisor(repository_reader=repo_reader, llm_provider=llm_provider)
                agent_params.update({
                    'repositorio': job_info['data']['repo_name'],
                    'nome_branch': job_info['data']['branch_name'],
                    'instrucoes_extras': job_info['data'].get('recomendations', job_info['data']['analysis_report'])
                })
                agent_response = agente_para_etapa.main(**agent_params)
            else:
                agente_para_etapa = AgenteProcessador(llm_provider=llm_provider)
                lightweight_changeset = {
                    "resumo_geral": previous_step_result.get("resumo_geral"),
                    "conjunto_de_mudancas": [
                        {"caminho_do_arquivo": m.get("caminho_do_arquivo"), "justificativa": m.get("justificativa")}
                        for m in previous_step_result.get("conjunto_de_mudancas", [])
                    ]
                }
                agent_params['codigo'] = lightweight_changeset
                agent_response = agente_para_etapa.main(**agent_params)

            json_string = agent_response['resultado']['reposta_final'].get('reposta_final', '')
            if not json_string.strip():
                raise ValueError(f"A IA retornou uma resposta vazia para a etapa '{job_info['status']}'.")
            
            current_step_result = json.loads(json_string.replace("```json", "").replace("```", "").strip())
            
            if i == 0:
                job_info['data']['resultado_refatoracao'] = current_step_result
            else:
                job_info['data']['resultado_agrupamento'] = current_step_result
            
            previous_step_result = current_step_result

        job_store.set_job(job_id, job_info)

        job_info['status'] = 'populating_data'
        job_store.set_job(job_id, job_info)
        
        refatoracao_data = job_info['data'].get('resultado_refatoracao', {})
        agrupamento_data = job_info['data'].get('resultado_agrupamento', {})
        
        job_info['data']['diagnostic_logs'] = {
            "1_json_refatoracao_inicial": refatoracao_data,
            "2_json_agrupamento_recebido": agrupamento_data
        }
        
        dados_preenchidos = changeset_filler.main(
            json_agrupado=agrupamento_data,
            json_inicial=refatoracao_data
        )
        
        dados_finais_formatados = {"resumo_geral": dados_preenchidos.get("resumo_geral", ""), "grupos": []}
        for nome_grupo, detalhes_pr in dados_preenchidos.items():
            if nome_grupo == "resumo_geral": continue
            dados_finais_formatados["grupos"].append({"branch_sugerida": nome_grupo, "titulo_pr": detalhes_pr.get("resumo_do_pr", ""), "resumo_do_pr": detalhes_pr.get("descricao_do_pr", ""), "conjunto_de_mudancas": detalhes_pr.get("conjunto_de_mudancas", [])})
        
        job_info['status'] = 'committing_to_github'
        job_store.set_job(job_id, job_info)
        
        commit_results = commit_multiplas_branchs.processar_e_subir_mudancas_agrupadas(
            nome_repo=job_info['data']['repo_name'], 
            dados_agrupados=dados_finais_formatados
        )
        job_info['data']['commit_details'] = commit_results
      
        job_info['status'] = 'completed'
        job_store.set_job(job_id, job_info)
        print(f"[{job_id}] Processo concluído com sucesso!")

    except Exception as e:
        traceback.print_exc()
        handle_task_exception(job_id, e, job_info.get('status', 'run_workflow') if job_info else 'run_workflow')


# --- Endpoints da API ---

@app.post("/start-analysis", response_model=StartAnalysisResponse, tags=["Jobs"])
def start_analysis(payload: StartAnalysisPayload, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    initial_job_data = {
        'status': 'starting',
        'data': {
            'repo_name': payload.repo_name,
            'branch_name': payload.branch_name,
            'original_analysis_type': payload.analysis_type,
            'instrucoes_extras': payload.instrucoes_extras,
            'model_name': payload.model_name # Salva o modelo escolhido para uso futuro
        },
        'error_details': None
    }
    job_store.set_job(job_id, initial_job_data)
    background_tasks.add_task(run_report_generation_task, job_id, payload)
    return StartAnalysisResponse(job_id=job_id)

@app.post("/update-job-status", response_model=Dict[str, str], tags=["Jobs"])
def update_job_status(payload: UpdateJobPayload, background_tasks: BackgroundTasks):
    job = job_store.get_job(payload.job_id)
    if not job: raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")
    
    if job['status'] not in ['pending_approval']:
        if job['status'] == 'completed':
            return {"job_id": payload.job_id, "status": "completed", "message": "Este job já foi concluído."}
        raise HTTPException(status_code=400, detail=f"O job não pode ser modificado. Status atual: {job['status']}")
    
    if payload.action == 'approve':
        if payload.observacoes:
            job['data']['observacoes_aprovacao'] = payload.observacoes
        
        job['status'] = 'workflow_started'
        job_store.set_job(payload.job_id, job)
        
        background_tasks.add_task(run_workflow_task, payload.job_id)
        return {"job_id": payload.job_id, "status": "workflow_started", "message": "Aprovação recebida. Processo iniciado."}
    
    if payload.action == 'reject':
        job['status'] = 'rejected'
        job_store.set_job(payload.job_id, job)
        return {"job_id": payload.job_id, "status": "rejected", "message": "Processo encerrado."}

@app.get("/jobs/{job_id}/report", response_model=ReportResponse, tags=["Jobs"])
def get_job_report(job_id: str = Path(..., title="O ID do Job para buscar o relatório")):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")
    
    report = job.get("data", {}).get("analysis_report")
    if not report:
        raise HTTPException(status_code=404, detail=f"Relatório não encontrado para este job. Status: {job.get('status')}")

    return ReportResponse(job_id=job_id, analysis_report=report)

@app.get("/status/{job_id}", response_model=FinalStatusResponse, tags=["Jobs"])
def get_status(job_id: str = Path(..., title="O ID do Job a ser verificado")):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")

    status = job.get('status')
    logs = job.get("data", {}).get("diagnostic_logs")

    try:
        if status == 'completed':
            if job.get("data", {}).get("gerar_relatorio_apenas") is True:
                return FinalStatusResponse(
                    job_id=job_id,
                    status=status,
                    analysis_report=job.get("data", {}).get("analysis_report")
                )
            else:
                summary_list = []
                commit_details = job.get("data", {}).get("commit_details", [])
                for pr_info in commit_details:
                    if pr_info.get("success") and pr_info.get("pr_url"):
                        summary_list.append(
                            PullRequestSummary(
                                pull_request_url=pr_info.get("pr_url"),
                                branch_name=pr_info.get("branch_name"),
                                arquivos_modificados=pr_info.get("arquivos_modificados", [])
                            )
                        )
                return FinalStatusResponse(
                    job_id=job_id, 
                    status=status, 
                    summary=summary_list,
                    diagnostic_logs=logs
                )
        elif status == 'failed':
            return FinalStatusResponse(
                job_id=job_id,
                status=status,
                error_details=job.get("error_details", "Nenhum detalhe de erro encontrado."),
                diagnostic_logs=logs
            )
        else:
            return FinalStatusResponse(job_id=job_id, status=status)
    except ValidationError as e:
        print(f"ERRO CRÍTICO de Validação no Job ID {job_id}: {e}")
        print(f"Dados brutos do job que causaram o erro: {job}")
        raise HTTPException(status_code=500, detail="Erro interno ao formatar a resposta do status do job.")







