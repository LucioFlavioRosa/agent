# Arquivo: mcp_server_fastapi.py (VERSÃO COMPLETA E FINAL)

import json
import uuid
from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware

# --- Módulos do seu projeto (Processos Separados) ---
from tools.job_store import set_job, get_job             # Gerenciador de estado
from agents import agente_revisor                       # Agente de análise (orquestra leitura + IA)
from tools import preenchimento, commit_multiplas_branchs # Ferramentas de pós-processamento

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
    commit_details: Optional[List[Dict[str, Any]]] = Field(None, description="Detalhes sobre os commits e PRs criados.")
    error_details: Optional[str] = Field(None, description="Detalhes do erro, se o job falhou.")

class UpdateJobPayload(BaseModel):
    job_id: str
    action: Literal["approve", "reject"]
    observacoes: Optional[str] = None

# --- Configuração do Servidor FastAPI ---
app = FastAPI(
    title="MCP Server - Multi-Agent Code Platform",
    description="Servidor robusto com Redis para orquestrar agentes de IA para análise e refatoração de código.",
    version="4.1.0" # Versão com a correção final do workflow
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
    error_text = str(e)
    error_message = f"Erro fatal durante a etapa '{step}': {error_text}"
    
    print(f"[{job_id}] {error_message}")
    try:
        job_info = get_job(job_id)
        if job_info:
            job_info['status'] = 'failed'
            job_info['error_details'] = error_message
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

        job_info['status'] = 'reading_repository'
        set_job(job_id, job_info)
        print(f"[{job_id}] Etapa 1: Delegando leitura do repositório e análise para o agente...")
        
        resposta_agente = agente_revisor.main(
            tipo_analise=payload.analysis_type,
            repositorio=payload.repo_name,
            nome_branch=payload.branch_name,
            instrucoes_extras=payload.instrucoes_extras
        )
        
        full_llm_response_obj = resposta_agente['resultado']['reposta_final']
        report_text_only = full_llm_response_obj['reposta_final']

        job_info['status'] = 'pending_approval'
        job_info['data']['analysis_report'] = report_text_only
        set_job(job_id, job_info)
        print(f"[{job_id}] Relatório gerado com sucesso. Job aguardando aprovação.")
        
    except Exception as e:
        current_step = job_info.get('status', 'report_generation') if job_info else 'report_generation'
        handle_task_exception(job_id, e, current_step)

# Em mcp_server_fastapi.py

# Em mcp_server_fastapi.py

def run_workflow_task(job_id: str):
    try:
        print(f"[{job_id}] Iniciando workflow...")
        job_info = jobs[job_id]
        original_analysis_type = job_info['data']['original_analysis_type']
        workflow = WORKFLOW_REGISTRY.get(original_analysis_type)
        if not workflow: raise ValueError(f"Nenhum workflow definido para: {original_analysis_type}")
        
        resultado_refatoracao, resultado_agrupamento = None, None
        previous_step_result = None
        for i, step in enumerate(workflow['steps']):
            job_info['status'] = step['status_update']
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
                # [CORREÇÃO APLICADA AQUI]
                # Converte o dicionário do passo anterior para uma string JSON bem formatada.
                # A IA entende este formato universalmente.
                agent_params['codigo'] = json.dumps(previous_step_result, indent=2, ensure_ascii=False)
            
            agent_response = step['agent_function'](**agent_params)
            json_string = agent_response['resultado']['reposta_final'].replace("```json", '').replace("```", '')
            previous_step_result = json.loads(json_string)
            if i == 0: resultado_refatoracao = previous_step_result
            else: resultado_agrupamento = previous_step_result
        
        job_info['status'] = 'populating_data'
        print(f"[{job_id}] ... Etapa de preenchimento...")
        dados_preenchidos = preenchimento.main(json_agrupado=resultado_agrupamento, json_inicial=resultado_refatoracao)
        
        print(f"[{job_id}] ... Etapa de transformação...")
        dados_finais_formatados = {"resumo_geral": dados_preenchidos.get("resumo_geral", ""), "grupos": []}
        for nome_grupo, detalhes_pr in dados_preenchidos.items():
            if nome_grupo == "resumo_geral": continue
            dados_finais_formatados["grupos"].append({"branch_sugerida": nome_grupo, "titulo_pr": detalhes_pr.get("resumo_do_pr", ""), "resumo_do_pr": detalhes_pr.get("descricao_do_pr", ""), "conjunto_de_mudancas": detalhes_pr.get("conjunto_de_mudancas", [])})
        
        if not dados_finais_formatados.get("grupos"): raise ValueError("Dados para commit vazios.")

        job_info['status'] = 'committing_to_github'
        print(f"[{job_id}] ... Etapa de commit para o GitHub...")
        commit_multiplas_branchs.processar_e_subir_mudancas_agrupadas(nome_repo=job_info['data']['repo_name'], dados_agrupados=dados_finais_formatados)
        job_info['status'] = 'completed'
        print(f"[{job_id}] Processo concluído com sucesso!")
    except Exception as e:
        print(f"ERRO FATAL na tarefa [{job_id}]: {e}")
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = str(e)
# --- Endpoints da API ---

@app.post("/start-analysis", response_model=StartAnalysisResponse, tags=["Jobs"])
def start_analysis(payload: StartAnalysisPayload, background_tasks: BackgroundTasks):
    """
    Inicia um novo job de análise de código.
    """
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
    set_job(job_id, initial_job_data)
    
    background_tasks.add_task(run_report_generation_task, job_id, payload)
    
    return StartAnalysisResponse(job_id=job_id)

@app.post("/update-job-status", response_model=Dict[str, str], tags=["Jobs"])
def update_job_status(payload: UpdateJobPayload, background_tasks: BackgroundTasks):
    """
    Aprova ou rejeita um job que está aguardando aprovação.
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

# Endpoint de status simplificado para máxima compatibilidade durante a depuração.
@app.get("/status/{job_id}", tags=["Jobs"]) 
def get_status(job_id: str = Path(..., title="O ID do Job a ser verificado")):
    """
    Verifica o status e os resultados de um job a qualquer momento.
    Retorna o dicionário raw do Redis para evitar ValidationErrors durante o debug.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")

    return job


