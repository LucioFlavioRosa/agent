# Arquivo: mcp_server_fastapi.py (VERSÃO REATORADA PARA REDIS E AZURE)

import json
import uuid
from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware

# [ALTERADO] Importa as funções do nosso módulo de armazenamento Redis.
from tools.job_store import get_job, set_job

# --- Módulos do seu projeto (sem alterações) ---
from agents import agente_revisor
from tools import preenchimento, commit_multiplas_branchs

# --- Modelos de Dados (Pydantic) ---

# [RENOMEADO] Renomeado para refletir a ação inicial de forma mais clara.
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
    # [NOVO] Adicionados campos para um feedback mais rico ao cliente.
    files_read: Optional[List[str]] = Field(None, description="Lista de arquivos lidos do repositório.")
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
    description="Servidor robusto com Redis e fluxo de status deliberado para análise de código.",
    version="7.0.0" # Nova versão refatorada
)

# [BOA PRÁTICA] Middleware CORS para permitir requisições de front-ends.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# [RESTAURADO] O registro de workflows é essencial para a lógica de execução.
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


# --- Lógica das Tarefas em Background ---

def handle_task_exception(job_id: str, e: Exception, step: str):
    """Função centralizada para lidar com exceções nas tarefas de background."""
    error_message = f"Erro fatal durante a etapa '{step}': {e}"
    print(f"[{job_id}] {error_message}")
    try:
        job_info = get_job(job_id)
        if job_info:
            job_info['status'] = 'failed'
            job_info['error'] = error_message
            set_job(job_id, job_info)
    except Exception as redis_e:
        print(f"[{job_id}] ERRO CRÍTICO: Falha ao registrar o erro no Redis. Erro: {redis_e}")

# [RESTAURADA E ADAPTADA] A função de workflow principal, agora integrada com Redis.
def run_workflow_task(job_id: str):
    try:
        print(f"[{job_id}] Iniciando workflow completo...")
        job_info = get_job(job_id)
        if not job_info: raise ValueError("Job não encontrado no início do workflow.")

        original_analysis_type = job_info['data']['original_analysis_type']
        workflow = WORKFLOW_REGISTRY.get(original_analysis_type)
        if not workflow: raise ValueError(f"Nenhum workflow definido para: {original_analysis_type}")
        
        previous_step_result = None
        for i, step in enumerate(workflow['steps']):
            job_info['status'] = step['status_update']
            set_job(job_id, job_info) # Salva o status atual no Redis
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
            json_string = agent_response['resultado']['reposta_final'].replace("```json", '').replace("```", '')
            previous_step_result = json.loads(json_string)
            if i == 0: job_info['data']['resultado_refatoracao'] = previous_step_result
            else: job_info['data']['resultado_agrupamento'] = previous_step_result
        
        job_info['status'] = 'populating_data'
        set_job(job_id, job_info)
        print(f"[{job_id}] ... Etapa de preenchimento...")
        dados_preenchidos = preenchimento.main(
            json_agrupado=job_info['data']['resultado_agrupamento'],
            json_inicial=job_info['data']['resultado_refatoracao']
        )
        
        print(f"[{job_id}] ... Etapa de transformação de dados para commit...")
        dados_finais_formatados = {"resumo_geral": dados_preenchidos.get("resumo_geral", ""), "grupos": []}
        for nome_grupo, detalhes_pr in dados_preenchidos.items():
            if nome_grupo == "resumo_geral": continue
            dados_finais_formatados["grupos"].append({
                "branch_sugerida": nome_grupo,
                "titulo_pr": detalhes_pr.get("resumo_do_pr", ""),
                "resumo_do_pr": detalhes_pr.get("descricao_do_pr", ""),
                "conjunto_de_mudancas": detalhes_pr.get("conjunto_de_mudancas", [])
            })
        
        if not dados_finais_formatados.get("grupos"): raise ValueError("Dados para commit vazios.")

        job_info['status'] = 'committing_to_github'
        set_job(job_id, job_info)
        print(f"[{job_id}] ... Etapa de commit para o GitHub...")
        # [ALTERADO] A função de commit agora retorna os links dos PRs para armazenamento.
        commit_results = commit_multiplas_branchs.processar_e_subir_mudancas_agrupadas(
            nome_repo=job_info['data']['repo_name'],
            dados_agrupados=dados_finais_formatados
        )
        
        job_info['data']['commit_details'] = commit_results # Salva o resultado
        job_info['status'] = 'completed'
        set_job(job_id, job_info)
        print(f"[{job_id}] Processo concluído com sucesso!")

    except Exception as e:
        handle_task_exception(job_id, e, "run_workflow")

# --- Endpoints da API ---

@app.post("/jobs/start-analysis", response_model=StartAnalysisResponse, tags=["Jobs"])
def start_analysis(payload: StartAnalysisPayload, background_tasks: BackgroundTasks):
    """
    Inicia um novo job de análise, que começa gerando o relatório inicial da IA.
    """
    job_id = str(uuid.uuid4())
    # [ALTERADO] Estrutura de dados inicial explícita e limpa.
    initial_job_data = {
        'status': 'generating_report',
        'data': {
            'repo_name': payload.repo_name,
            'branch_name': payload.branch_name,
            'original_analysis_type': payload.analysis_type,
            'instrucoes_extras': payload.instrucoes_extras,
        },
        'error': None
    }
    set_job(job_id, initial_job_data)
    
    # [ALTERADO] O processo agora é um único fluxo contínuo.
    # O agente_revisor.main lê o repo e gera o relatório em uma única chamada.
    background_tasks.add_task(run_report_generation_task, job_id, payload)
    
    return StartAnalysisResponse(job_id=job_id)

def run_report_generation_task(job_id: str, payload: StartAnalysisPayload):
    """
    Tarefa de background que lê o repositório e gera o relatório de análise.
    """
    try:
        print(f"[{job_id}] Tarefa de geração de relatório iniciada...")
        resposta_agente = agente_revisor.main(
            tipo_analise=payload.analysis_type,
            repositorio=payload.repo_name,
            nome_branch=payload.branch_name,
            instrucoes_extras=payload.instrucoes_extras
        )
        report = resposta_agente['resultado']['reposta_final']
        
        job_info = get_job(job_id)
        job_info['status'] = 'pending_approval'
        job_info['data']['analysis_report'] = report
        # Opcional: Salvar os nomes dos arquivos lidos, se a função `main` os retornar.
        # job_info['data']['files_read'] = resposta_agente.get('files_read', [])
        
        set_job(job_id, job_info)
        print(f"[{job_id}] Relatório gerado. Job aguardando aprovação.")
        
    except Exception as e:
        handle_task_exception(job_id, e, "report_generation")

@app.post("/jobs/update-status", tags=["Jobs"])
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
        return {"job_id": payload.job_id, "status": "workflow_started", "message": "Processo de refatoração e commit iniciado em background."}
    
    if payload.action == 'reject':
        job['status'] = 'rejected'
        set_job(payload.job_id, job)
        return {"job_id": payload.job_id, "status": "rejected", "message": "Processo encerrado a pedido do usuário."}

@app.get("/jobs/status/{job_id}", response_model=JobStatusResponse, tags=["Jobs"])
def get_job_status(job_id: str = Path(..., title="O ID do Job a ser verificado")):
    """
    Verifica o status atual de um job.
    """
    job = get_job(job_id)
    if not job: raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")
    
    return JobStatusResponse(
        job_id=job_id,
        status=job['status'],
        files_read=job['data'].get('files_read'),
        analysis_report=job['data'].get('analysis_report'),
        commit_details=job['data'].get('commit_details'),
        error_details=job.get('error')
    )
