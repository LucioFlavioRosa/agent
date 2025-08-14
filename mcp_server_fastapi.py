# Arquivo: mcp_server_fastapi.py (VERSÃO FINAL - CORRIGIDA COM GITHUB READER)

import json
import uuid
import yaml
import importlib
from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, Literal, List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware

# --- Módulos do projeto ---
from tools.job_store import RedisJobStore
from tools import commit_multiplas_branchs

# --- Classes e dependências para montar os agentes e ferramentas ---
from agents.agente_revisor import AgenteRevisor
from tools.requisicao_openai import OpenAILLMProvider
from tools.rag_retriever import AzureAISearchRAGRetriever
from tools.preenchimento import ChangesetFiller
# --- MUDANÇA: CORRIGINDO O REPOSITORY READER ---
from tools.github_reader import GitHubRepositoryReader


# --- Modelos de Dados Pydantic (inalterados) ---
class StartAnalysisPayload(BaseModel):
    repo_name: str
    analysis_type: Literal["relatorio_analise_de_design_de_codigo", "relatorio_refatoracao_codigo",
                           "relatorio_documentacao_codigo", "relatorio_avaliacao_terraform",
                           "relatorio_conformidades"]
    branch_name: Optional[str] = None
    instrucoes_extras: Optional[str] = None
    usar_rag: bool = Field(False, description="Define se a análise deve usar a base de conhecimento RAG.")
    gerar_relatorio_apenas: bool = Field(False, description="Se True, executa apenas a geração do relatório inicial e finaliza.")

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
    summary: Optional[List[PullRequestSummary]] = Field(None, description="Resumo dos PRs e arquivos modificados.")
    error_details: Optional[str] = Field(None, description="Detalhes do erro, se o job falhou.")
    analysis_report: Optional[str] = Field(None, description="Relatório inicial da IA, se aplicável.")

class ReportResponse(BaseModel):
    job_id: str
    analysis_report: Optional[str]


# --- Configuração do Servidor FastAPI ---
app = FastAPI(
    title="MCP Server - Multi-Agent Code Platform",
    description="Servidor robusto com Redis para orquestrar agentes de IA para análise e refatoração de código.",
    version="8.1.0" # Version bump to reflect change
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

job_store = RedisJobStore()

def load_workflow_registry(filepath: str) -> dict:
    """
    Carrega a configuração de workflows de um arquivo YAML.
    A função agora apenas lê o arquivo, sem processar chaves dinâmicas.
    """
    print(f"Carregando workflows do arquivo: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

WORKFLOW_REGISTRY = load_workflow_registry("workflows.yaml")


# --- Funções de Tarefa (Tasks) ---

def handle_task_exception(job_id: str, e: Exception, step: str):
    error_text = str(e)
    error_message = f"Erro fatal durante a etapa '{step}': {error_text}"
    print(f"[{job_id}] {error_message}")
    try:
        job_info = job_store.get_job(job_id)
        if job_info:
            job_info['status'] = 'failed'
            job_info['error_details'] = error_message
            job_store.set_job(job_id, job_info)
    except Exception as redis_e:
        print(f"[{job_id}] ERRO CRÍTICO ADICIONAL: Falha ao registrar o erro no Redis. Erro: {redis_e}")

# Em mcp_server_fastapi.py, substitua as duas funções de tarefa:

def run_report_generation_task(job_id: str, payload: StartAnalysisPayload):
    job_info = None
    try:
        job_info = job_store.get_job(job_id)
        if not job_info: raise ValueError("Job não encontrado.")

        job_info['status'] = 'iniciando_a_analise'
        job_store.set_job(job_id, job_info)
        
        print(f"[{job_id}] Construindo o agente e suas dependências...")
        repo_reader = GitHubRepositoryReader()
        rag_retriever = AzureAISearchRAGRetriever()
        llm_provider = OpenAILLMProvider(rag_retriever=rag_retriever)
        agente = AgenteRevisor(repository_reader=repo_reader, llm_provider=llm_provider)

        print(f"[{job_id}] Delegando leitura e análise para o agente (RAG: {payload.usar_rag})...")
        job_info['status'] = 'comecando_analise_llm'
        job_store.set_job(job_id, job_info)

        resposta_agente = agente.main(
            tipo_analise=payload.analysis_type,
            repositorio=payload.repo_name,
            nome_branch=payload.branch_name,
            instrucoes_extras=payload.instrucoes_extras,
            usar_rag=payload.usar_rag
        )

        full_llm_response_obj = resposta_agente['resultado']['reposta_final']
        json_string_from_llm = full_llm_response_obj.get('reposta_final', '')

        if not json_string_from_llm.strip():
            raise ValueError("A IA retornou uma resposta vazia na etapa de geração de relatório.")

        # --- MUDANÇA CRÍTICA: Extrair o JSON já na primeira etapa ---
        print(f"[{job_id}] Resposta da IA recebida. Tentando extrair JSON estruturado e relatório em texto.")
        
        try:
            # Assume que a IA retorna um JSON que contém o relatório e as mudanças
            # Ex: { "resumo_geral": "...", "conjunto_de_mudancas": [...] }
            cleaned_json_string = json_string_from_llm.replace("```json", "").replace("```", "").strip()
            structured_changes = json.loads(cleaned_json_string)
            
            # O "relatório" para o humano pode ser uma parte do JSON ou o JSON inteiro formatado
            report_text_only = json.dumps(structured_changes, indent=2, ensure_ascii=False)
            
            # Salva AMBOS os resultados no job_info
            job_info['data']['analysis_report'] = report_text_only # Relatório para o humano
            job_info['data']['resultado_refatoracao'] = structured_changes # JSON para a máquina
            print(f"[{job_id}] JSON estruturado extraído com sucesso.")

        except json.JSONDecodeError:
            # Se a IA retornar apenas texto, usamos esse texto como relatório e o JSON fica vazio
            print(f"[{job_id}] AVISO: A resposta da IA não era um JSON válido. Tratando como relatório de texto puro.")
            job_info['data']['analysis_report'] = json_string_from_llm
            job_info['data']['resultado_refatoracao'] = {} # Deixa vazio para indicar que não há mudanças estruturadas

        if payload.gerar_relatorio_apenas:
            job_info['status'] = 'completed'
            print(f"[{job_id}] Relatório gerado. Processo finalizado conforme solicitado.")
        else:
            job_info['status'] = 'pending_approval'
            print(f"[{job_id}] Relatório gerado. Job aguardando aprovação.")

        job_info['data']['usar_rag'] = payload.usar_rag
        job_info['data']['gerar_relatorio_apenas'] = payload.gerar_relatorio_apenas
        job_store.set_job(job_id, job_info)

    except Exception as e:
        import traceback
        traceback.print_exc()
        current_step = job_info.get('status', 'report_generation') if job_info else 'report_generation'
        handle_task_exception(job_id, e, current_step)

def run_workflow_task(job_id: str):
    job_info = None
    try:
        job_info = job_store.get_job(job_id)
        if not job_info: raise ValueError("Job não encontrado no início do workflow.")
        
        print(f"[{job_id}] Construindo dependências para execução do workflow...")
        # A construção das dependências está correta.
        repo_reader = GitHubRepositoryReader()
        rag_retriever = AzureAISearchRAGRetriever()
        llm_provider = OpenAILLMProvider(rag_retriever=rag_retriever)
        agente = AgenteRevisor(repository_reader=repo_reader, llm_provider=llm_provider)
        changeset_filler = ChangesetFiller()

        print(f"[{job_id}] Iniciando workflow completo após aprovação...")
        usar_rag = job_info.get("data", {}).get("usar_rag", False)
        print(f"[{job_id}] Executando workflow com RAG: {usar_rag}")

        original_analysis_type = job_info['data']['original_analysis_type']
        workflow = WORKFLOW_REGISTRY.get(original_analysis_type)
        if not workflow: raise ValueError(f"Nenhum workflow definido para: {original_analysis_type}")
        
        # --- MUDANÇA CRÍTICA: Usar o JSON já processado ---
        # O resultado da refatoração já veio da primeira tarefa.
        previous_step_result = job_info['data'].get('resultado_refatoracao')
        
        # O loop agora começa do SEGUNDO passo do workflow (índice 1), pois o primeiro já foi feito.
        for step in workflow['steps'][1:]: # Começa do segundo item da lista
            job_info['status'] = step['status_update']
            job_store.set_job(job_id, job_info)
            print(f"[{job_id}] ... Executando passo: {job_info['status']}")
            
            agent_params = step['params'].copy()
            agent_params['usar_rag'] = usar_rag
            
            # O input para o agente de agrupamento agora é o JSON estruturado do passo anterior.
            lightweight_changeset = {
                "resumo_geral": previous_step_result.get("resumo_geral"),
                "conjunto_de_mudancas": [
                    {"caminho_do_arquivo": m.get("caminho_do_arquivo"), "justificativa": m.get("justificativa")}
                    for m in previous_step_result.get("conjunto_de_mudancas", [])
                ]
            }
            agent_params['codigo'] = json.dumps(lightweight_changeset, indent=2, ensure_ascii=False)
            
            agent_response = agente.main(**agent_params)
            
            # ... (o resto do processamento da resposta da IA continua o mesmo)
            full_llm_response_obj = agent_response['resultado']['reposta_final']
            json_string_from_llm = full_llm_response_obj.get('reposta_final', '')
            if not json_string_from_llm.strip():
                raise ValueError(f"A IA retornou uma resposta vazia para a etapa '{job_info['status']}'.")
            cleaned_json_string = json_string_from_llm.replace("```json", "").replace("```", "").strip()
            
            # Atualiza o previous_step_result para o próximo passo do loop (se houver)
            previous_step_result = json.loads(cleaned_json_string)

        # Salva o resultado final do agrupamento
        job_info['data']['resultado_agrupamento'] = previous_step_result
        job_store.set_job(job_id, job_info)
        
        job_info['status'] = 'populating_data'
        job_store.set_job(job_id, job_info)
        
        dados_preenchidos = changeset_filler.main(
            json_agrupado=job_info['data']['resultado_agrupamento'],
            json_inicial=job_info['data']['resultado_refatoracao']
        )
        
        # ... (o resto da função para formatar e commitar os dados continua o mesmo)

    except Exception as e:
        import traceback
        traceback.print_exc()
        current_step = job_info.get('status', 'run_workflow') if job_info else 'run_workflow'
        handle_task_exception(job_id, e, current_step)


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
                                arquivos_modificados=pr_info.get("arquivos_modificados", []) # Ajuste se o nome do campo for diferente
                            )
                        )
                return FinalStatusResponse(job_id=job_id, status=status, summary=summary_list)

        elif status == 'failed':
            return FinalStatusResponse(
                job_id=job_id,
                status=status,
                error_details=job.get("error_details", "Nenhum detalhe de erro encontrado.")
            )
        
        else:
            return FinalStatusResponse(job_id=job_id, status=status)

    except ValidationError as e:
        print(f"ERRO CRÍTICO de Validação no Job ID {job_id}: {e}")
        print(f"Dados brutos do job que causaram o erro: {job}")
        raise HTTPException(status_code=500, detail="Erro interno ao formatar a resposta do status do job.")



