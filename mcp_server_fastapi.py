# Arquivo: mcp_server_fastapi.py (VERSÃO COM RESPOSTA DE STATUS REFINADA)

import json
import uuid
from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, Literal, List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware

# --- Módulos do projeto ---
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

class UpdateJobPayload(BaseModel):
    job_id: str
    action: Literal["approve", "reject"]
    observacoes: Optional[str] = None

# [NOVO] Modelos para a resposta final resumida, melhorando a experiência do usuário.
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


# --- Configuração do Servidor FastAPI ---
app = FastAPI(
    title="MCP Server - Multi-Agent Code Platform",
    description="Servidor robusto com Redis para orquestrar agentes de IA para análise e refatoração de código.",
    version="8.0.0" # Versão com UX aprimorada
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
    # ... outros workflows
}

# --- Lógica de Tarefas em Background (sem alterações) ---

def handle_task_exception(job_id: str, e: Exception, step: str):
    # ... (código inalterado)
# ... (demais funções de background permanecem inalteradas)
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
    job_info = None
    try:
        job_info = get_job(job_id)
        if not job_info: raise ValueError("Job não encontrado.")

        job_info['status'] = 'reading_repository'
        set_job(job_id, job_info)
        print(f"[{job_id}] Etapa 1: Delegando leitura e análise para o agente...")
        
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

def run_workflow_task(job_id: str):
    job_info = None
    try:
        job_info = get_job(job_id)
        if not job_info: raise ValueError("Job não encontrado.")
        
        print(f"[{job_id}] Iniciando workflow completo...")
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
                lightweight_changeset = {
                    "resumo_geral": previous_step_result.get("resumo_geral"),
                    "conjunto_de_mudancas": [
                        {
                            "caminho_do_arquivo": mudanca.get("caminho_do_arquivo"),
                            "justificativa": mudanca.get("justificativa")
                        }
                        for mudanca in previous_step_result.get("conjunto_de_mudancas", [])
                    ]
                }
                agent_params['codigo'] = json.dumps(lightweight_changeset, indent=2, ensure_ascii=False)
            
            agent_response = step['agent_function'](**agent_params)
            
            full_llm_response_obj = agent_response['resultado']['reposta_final']
            json_string_from_llm = full_llm_response_obj.get('reposta_final', '')

            if not json_string_from_llm or not json_string_from_llm.strip():
                raise ValueError(f"A IA retornou uma resposta vazia para a etapa '{job_info['status']}'.")

            cleaned_json_string = json_string_from_llm.replace("```json", "").replace("```", "").strip()
            previous_step_result = json.loads(cleaned_json_string)

            if i == 0:
                job_info['data']['resultado_refatoracao'] = previous_step_result
            else:
                job_info['data']['resultado_agrupamento'] = previous_step_result
            set_job(job_id, job_info)
        
        job_info['status'] = 'populating_data'
        set_job(job_id, job_info)
        
        dados_preenchidos = preenchimento.main(
            json_agrupado=job_info['data']['resultado_agrupamento'],
            json_inicial=job_info['data']['resultado_refatoracao']
        )
        
        dados_finais_formatados = {"resumo_geral": dados_preenchidos.get("resumo_geral", ""), "grupos": []}
        for nome_grupo, detalhes_pr in dados_preenchidos.items():
            if nome_grupo == "resumo_geral": continue
            dados_finais_formatados["grupos"].append({"branch_sugerida": nome_grupo, "titulo_pr": detalhes_pr.get("resumo_do_pr", ""), "resumo_do_pr": detalhes_pr.get("descricao_do_pr", ""), "conjunto_de_mudancas": detalhes_pr.get("conjunto_de_mudancas", [])})
        
        if not dados_finais_formatados.get("grupos"): raise ValueError("Dados para commit vazios.")

        job_info['status'] = 'committing_to_github'
        set_job(job_id, job_info)
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
    # ... (código inalterado)
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
    # ... (código inalterado)
    job = get_job(payload.job_id)
    if not job: raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")
    if job['status'] != 'pending_approval': raise HTTPException(status_code=400, detail=f"O job não pode ser modificado. Status atual: {job['status']}")
    
    if payload.action == 'approve':
        if payload.observacoes:
            job['data']['observacoes_aprovacao'] = payload.observacoes
        job['status'] = 'workflow_started'
        set_job(payload.job_id, job)
        background_tasks.add_task(run_workflow_task, payload.job_id)
        return {"job_id": payload.job_id, "status": "workflow_started", "message": "Aprovação recebida."}
    
    if payload.action == 'reject':
        job['status'] = 'rejected'
        set_job(payload.job_id, job)
        return {"job_id": payload.job_id, "status": "rejected", "message": "Processo encerrado."}


@app.get("/status/{job_id}", response_model=FinalStatusResponse, tags=["Jobs"]) 
def get_status(job_id: str = Path(..., title="O ID do Job a ser verificado")):
    """
    Verifica o status de um job. Retorna uma resposta estruturada e segura
    com resumos para os estados 'completed' e 'failed'.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")

    status = job.get('status')
    
    try:
        # Caso 1: Job concluído com sucesso. Monta o resumo detalhado.
        if status == 'completed':
            summary_list = []
            commit_details = job.get("data", {}).get("commit_details", [])
            dados_agrupados = job.get("data", {}).get("resultado_agrupamento", {})

            mapa_arquivos_por_branch = {}
            for nome_grupo, detalhes_grupo in dados_agrupados.items():
                if isinstance(detalhes_grupo, dict) and 'conjunto_de_mudancas' in detalhes_grupo:
                    arquivos = [m.get("caminho_do_arquivo") for m in detalhes_grupo.get("conjunto_de_mudancas", []) if m]
                    mapa_arquivos_por_branch[nome_grupo] = arquivos

            for pr_info in commit_details:
                branch_name = pr_info.get("branch_name")
                if pr_info.get("success") and pr_info.get("pr_url"):
                    summary_list.append(
                        PullRequestSummary(
                            pull_request_url=pr_info.get("pr_url"),
                            branch_name=branch_name,
                            arquivos_modificados=mapa_arquivos_por_branch.get(branch_name, [])
                        )
                    )
            
            return FinalStatusResponse(
                job_id=job_id,
                status=status,
                summary=summary_list
            )

        # Caso 2: Job falhou. Retorna apenas os detalhes do erro.
        elif status == 'failed':
            return FinalStatusResponse(
                job_id=job_id,
                status=status,
                error_details=job.get("error_details", "Nenhum detalhe de erro encontrado.")
            )
        
        # Caso 3: Job em andamento. Retorna o relatório para aprovação ou apenas o status.
        else:
            return FinalStatusResponse(
                job_id=job_id,
                status=status,
                analysis_report=job.get("data", {}).get("analysis_report")
            )

    except ValidationError as e:
        # Bloco de segurança final: se a validação do Pydantic falhar,
        # loga o erro e retorna uma resposta de erro limpa, evitando o erro 500.
        print(f"ERRO CRÍTICO de Validação no Job ID {job_id}: {e}")
        print(f"Dados brutos do job que causaram o erro: {job}")
        raise HTTPException(status_code=500, detail="Erro interno ao formatar a resposta do status do job.")
