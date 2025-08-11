# Arquivo: mcp_server_fastapi.py (VERSÃO COMPLETA E FINAL)

import json
import uuid
from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware

# --- Módulos do seu projeto ---
from tools.job_store import set_job, get_job
from agents import agente_revisor
from tools import preenchimento, commit_multiplas_branchs

# --- Modelos de Dados Pydantic ---

class StartAnalysisPayload(BaseModel):
    repo_name: str
    analysis_type: Literal["design", "relatorio_teste_unitario"]
    branch_name: Optional[str] = None
    instrucoes_extras: Optional[str] = None

class StartAnalysisResponse(BaseModel):
    job_id: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    analysis_report: Optional[str] = Field(None, description="Relatório gerado pela IA para aprovação.")
    commit_details: Optional[Dict[str, Any]] = Field(None, description="Detalhes sobre os commits e PRs criados.")
    error_details: Optional[str] = Field(None, description="Detalhes do erro, se o job falhou.")

class UpdateJobPayload(BaseModel):
    job_id: str
    action: Literal["approve", "reject"]
    observacoes: Optional[str] = None

# --- Configuração do Servidor FastAPI ---
app = FastAPI(
    title="MCP Server - Multi-Agent Code Platform",
    description="Servidor robusto com Redis para orquestrar agentes de IA para análise e refatoração de código.",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- WORKFLOW_REGISTRY ---
WORKFLOW_REGISTRY = {
    "design": {
        "description": "Analisa o design, refatora o código e agrupa os commits.",
        "steps": [{"status_update": "refactoring_code", "agent_function": agente_revisor.main, "params": {"tipo_analise": "refatoracao"}},
                  {"status_update": "grouping_commits", "agent_function": agente_revisor.main, "params": {"tipo_analise": "agrupamento_design"}}]
    },
    "relatorio_teste_unitario": {
        "description": "Cria testes unitários com base no relatório e os agrupa.",
        "steps": [{"status_update": "writing_unit_tests", "agent_function": agente_revisor.main, "params": {"tipo_analise": "escrever_testes"}},
                  {"status_update": "grouping_tests", "agent_function": agente_revisor.main, "params": {"tipo_analise": "agrupamento_testes"}}]
    }
}

# --- Lógica de Tarefas em Background ---

def handle_task_exception(job_id: str, e: Exception, step: str):
    """Função centralizada para lidar com exceções e atualizar o status no Redis."""
    error_message = f"Erro fatal durante a etapa '{step}': {e}"
    print(f"[{job_id}] {error_message}")
    try:
        job_info = get_job(job_id)
        if job_info:
            job_info['status'] = 'failed'
            job_info['error'] = error_message
            set_job(job_id, job_info)
    except Exception as redis_e:
        print(f"[{job_id}] ERRO CRÍTICO ADICIONAL: Falha ao registrar o erro no Redis. Erro: {redis_e}")

def run_report_generation_task(job_id: str, payload: StartAnalysisPayload):
    """
    Tarefa de background que lê o repositório e gera o relatório de análise inicial.
    """
    job_info = None
    try:
        job_info = get_job(job_id)
        if not job_info: raise ValueError("Job não encontrado no início da geração do relatório.")

        # Define o status inicial para indicar a leitura do repositório
        job_info['status'] = 'reading_repository'
        set_job(job_id, job_info)
        print(f"[{job_id}] Etapa 1: Lendo repositório...")
        
        # A chamada para o agente que fará a leitura e a análise
        resposta_agente = agente_revisor.main(
            tipo_analise=payload.analysis_type,
            repositorio=payload.repo_name,
            nome_branch=payload.branch_name,
            instrucoes_extras=payload.instrucoes_extras
        )
        
        # O backend extrai a resposta final que deve ser um JSON string
        report = resposta_agente['resultado']['reposta_final']
        
        # Atualiza o status para indicar que o job aguarda aprovação
        job_info['status'] = 'pending_approval'
        job_info['data']['analysis_report'] = report
        set_job(job_id, job_info)
        print(f"[{job_id}] Relatório gerado. Job aguardando aprovação do usuário.")
        
    except Exception as e:
        # Usa o 'status' atual do job_info para um erro mais preciso, se disponível
        current_step = job_info.get('status', 'report_generation') if job_info else 'report_generation'
        handle_task_exception(job_id, e, current_step)

def run_workflow_task(job_id: str):
    """
    Tarefa principal que executa o workflow completo após a aprovação do usuário.
    """
    job_info = None
    try:
        job_info = get_job(job_id)
        if not job_info: raise ValueError("Job não encontrado no início do workflow.")
        
        print(f"[{job_id}] Iniciando workflow completo após aprovação...")

        original_analysis_type = job_info['data']['original_analysis_type']
        workflow = WORKFLOW_REGISTRY.get(original_analysis_type)
        if not workflow: raise ValueError(f"Nenhum workflow definido para: {original_analysis_type}")
        
        previous_step_result = None
        for i, step in enumerate(workflow['steps']):
            job_info['status'] = step['status_update'] 
            set_job(job_id, job_info)
            print(f"[{job_id}] ... Executando passo: {job_info['status']}")
            
            agent_params = step['params'].copy()
            
            if i == 0:
                relatorio_gerado = job_info['data']['analysis_report']
                instrucoes_iniciais = job_info['data'].get('instrucoes_extras')
                observacoes_aprovacao = job_info['data'].get('observacoes_aprovacao')

                instrucoes_completas = relatorio_gerado
                if instrucoes_iniciais:
                    instrucoes_completas += f"\n\n--- INSTRUÇÕES ADICIONAIS DO USUÁRIO (INICIAL) ---\n{instrucoes_iniciais}"
                if observacoes_aprovacao:
                    instrucoes_completas += f"\n\n--- OBSERVAÇÕES DA APROVAÇÃO (APLICAR COM PRIORIDADE) ---\n{observacoes_aprovacao}"
                
                agent_params.update({
                    'repositorio': job_info['data']['repo_name'],
                    'nome_branch': job_info['data']['branch_name'],
                    'instrucoes_extras': instrucoes_completas
                })
            else:
                agent_params['codigo'] = str(previous_step_result)
            
            agent_response = step['agent_function'](**agent_params)
            json_string = agent_response['resultado']['reposta_final']
            previous_step_result = json.loads(json_string)

            if i == 0: job_info['data']['resultado_refatoracao'] = previous_step_result
            else: job_info['data']['resultado_agrupamento'] = previous_step_result
            set_job(job_id, job_info)
        
        job_info['status'] = 'populating_data'
        set_job(job_id, job_info)
        dados_preenchidos = preenchimento.main(json_agrupado=job_info['data']['resultado_agrupamento'], json_inicial=job_info['data']['resultado_refatoracao'])
        
        dados_finais_formatados = {"resumo_geral": dados_preenchidos.get("resumo_geral", ""), "grupos": []}
        for nome_grupo, detalhes_pr in dados_preenchidos.items():
            if nome_grupo == "resumo_geral": continue
            dados_finais_formatados["grupos"].append({"branch_sugerida": nome_grupo, "titulo_pr": detalhes_pr.get("resumo_do_pr", ""), "resumo_do_pr": detalhes_pr.get("descricao_do_pr", ""), "conjunto_de_mudancas": detalhes_pr.get("conjunto_de_mudancas", [])})
        
        if not dados_finais_formatados.get("grupos"): raise ValueError("Dados para commit vazios.")

        job_info['status'] = 'committing_to_github'
        set_job(job_id, job_info)
        print(f"[{job_id}] ... Etapa de commit para o GitHub...")
        commit_results = commit_multiplas_branchs.processar_e_subir_mudancas_agrupadas(nome_repo=job_info['data']['repo_name'], dados_agrupados=dados_finais_formatados)
        
        job_info['data']['commit_details'] = commit_results
        job_info['status'] = 'completed'
        set_job(job_id, job_info)
        print(f"[{job_id}] Processo concluído com sucesso!")

    except Exception as e:
        current_step = job_info.get('status', 'run_workflow') if job_info else 'run_workflow'
        handle_task_exception(job_id, e, current_step)


# --- Endpoints da API ---

@app.post("/start-analysis", response_model=StartAnalysisResponse, tags=["Jobs"])
def start_analysis(payload: StartAnalysisPayload, background_tasks: BackgroundTasks):
    """
    Inicia um novo job, começando pela leitura do repo e geração do relatório.
    Retorna imediatamente com um Job ID para monitoramento.
    """
    job_id = str(uuid.uuid4())
    initial_job_data = {
        'status': 'generating_report', # Status inicial que o cliente verá
        'data': {
            'repo_name': payload.repo_name,
            'branch_name': payload.branch_name,
            'original_analysis_type': payload.analysis_type,
            'instrucoes_extras': payload.instrucoes_extras,
        },
        'error': None
    }
    set_job(job_id, initial_job_data)
    
    background_tasks.add_task(run_report_generation_task, job_id, payload)
    
    return StartAnalysisResponse(job_id=job_id)

@app.post("/update-job-status", tags=["Jobs"])
def update_job_status(payload: UpdateJobPayload, background_tasks: BackgroundTasks):
    """
    Aprova ou rejeita um job que está aguardando aprovação.
    A aprovação dispara o workflow principal de refatoração e commit.
    """
    job = get_job(payload.job_id)
    if not job: raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")
    if job['status'] != 'pending_approval': raise HTTPException(status_code=400, detail=f"O job não pode ser modificado. Status atual: {job['status']}")
    
    if payload.action == 'approve':
        if payload.observacoes:
            job['data']['observacoes_aprovacao'] = payload.observacoes
        
        job['status'] = 'workflow_started'
        set_job(payload.job_id, job)
        
        background_tasks.add_task(run_workflow_task, payload.job_id)
        return {"job_id": payload.job_id, "status": "workflow_started", "message": "Aprovação recebida. Processo de refatoração e commit iniciado."}
    
    if payload.action == 'reject':
        job['status'] = 'rejected'
        set_job(payload.job_id, job)
        return {"job_id": payload.job_id, "status": "rejected", "message": "Processo encerrado a pedido do usuário."}

@app.get("/status/{job_id}", response_model=JobStatusResponse, tags=["Jobs"])
def get_status(job_id: str = Path(..., title="O ID do Job a ser verificado")):
    """
    Verifica o status e os resultados de um job a qualquer momento.
    """
    job = get_job(job_id)
    if not job: raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")
    
    return JobStatusResponse(
        job_id=job_id,
        status=job['status'],
        analysis_report=job['data'].get('analysis_report'),
        commit_details=job['data'].get('commit_details'),
        error_details=job.get('error')
    )
