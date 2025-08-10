# Arquivo: mcp_server_fastapi.py (VERSÃO 5.3 - JOB STORE MODULARIZADO)

import json
import uuid
from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel
from typing import Optional, Literal, List, Dict
from fastapi.middleware.cors import CORSMiddleware

# [ALTERADO] O import agora reflete que job_store.py está dentro da pasta 'tools'
from tools.job_store import get_job, set_job

# --- Módulos do seu projeto ---
from agents import agente_revisor
from tools import preenchimento, commit_multiplas_branchs, job_store

# --- Modelos de Dados (Pydantic) ---
class StartJobPayload(BaseModel):
    repo_name: str
    analysis_type: Literal["design", "relatorio_teste_unitario"]
    branch_name: Optional[str] = None
    instrucoes_extras: Optional[str] = None

class StartJobResponse(BaseModel):
    job_id: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    files_read: Optional[List[str]] = None
    analysis_report: Optional[str] = None
    error_details: Optional[str] = None
    commit_links: Optional[List[Dict[str, str]]] = None

class UpdateJobPayload(BaseModel):
    job_id: str
    action: Literal["approve", "reject"]
    observacoes: Optional[str] = None

# --- Configuração do Servidor FastAPI ---
app = FastAPI(
    title="MCP Server - Multi-Agent Code Platform",
    description="Servidor robusto com report de commits em tempo real.",
    version="5.3.0"
)

# Configuração do CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# [REMOVIDO] A lógica do Redis foi movida para tools/job_store.py

# Registro de workflows pós-aprovação
WORKFLOW_REGISTRY = {
    "design": {
        "description": "Analisa o design, refatora o código e agrupa os commits.",
        "steps": [
            {"agent_function": agente_revisor.main, "params": {"tipo_analise": "refatoracao"}},
            {"agent_function": agente_revisor.main, "params": {"tipo_analise": "agrupamento_design"}}
        ]
    },
    "relatorio_teste_unitario": {
        "description": "Cria testes unitários com base no relatório e os agrupa.",
        "steps": [
            {"agent_function": agente_revisor.main, "params": {"tipo_analise": "escrever_testes"}},
            {"agent_function": agente_revisor.main, "params": {"tipo_analise": "agrupamento_testes"}}
        ]
    }
}

# --- Lógica das Tarefas em Background ---
# (Nenhuma alteração na lógica das tarefas, pois elas já usam get_job e set_job)
def run_file_reading_task(job_id: str, payload: StartJobPayload):
    try:
        job_info = job_store.get_job(job_id)
        job_info['status'] = 'lendo_repositorio'
        job_store.set_job(job_id, job_info)
        print(f"[{job_id}] Tarefa de leitura de arquivos iniciada...")
        
        codigo_com_conteudo = agente_revisor.ler_codigo_do_repositorio(
            repositorio=payload.repo_name,
            tipo_analise=payload.analysis_type,
            nome_branch=payload.branch_name
        )
        nomes_dos_arquivos = list(codigo_com_conteudo.keys())

        job_info['status'] = 'files_read_awaits_analysis'
        job_info['data']['files_read'] = nomes_dos_arquivos
        job_info['data']['codigo_com_conteudo'] = codigo_com_conteudo
        job_info['data'].update(payload.dict(exclude_unset=False)) 
        job_store.set_job(job_id, job_info)
        print(f"[{job_id}] Leitura concluída. Aguardando comando para iniciar análise.")
    except Exception as e:
        job_info = get_job(job_id)
        if job_info:
            job_info['status'] = 'failed'
            job_info['error'] = str(e)
            job_store.set_job(job_id, job_info)
        print(f"ERRO FATAL na tarefa de leitura [{job_id}]: {e}")

def run_report_generation_task(job_id: str):
    try:
        job_info = get_job(job_id)
        job_info['status'] = 'gerando_relatorio_ia'
        job_store.set_job(job_id, job_info)
        print(f"[{job_id}] Tarefa de geração de relatório iniciada...")

        codigo_com_conteudo = job_info['data']['codigo_com_conteudo']
        payload_dict = job_info['data']

        resposta_agente = agente_revisor.gerar_relatorio_analise(
            tipo_analise=payload_dict['analysis_type'],
            codigo_para_analise=codigo_com_conteudo,
            instrucoes_extras=payload_dict.get('instrucoes_extras')
        )
        report = resposta_agente['reposta_final']
        
        job_info['status'] = 'pending_approval'
        job_info['data']['analysis_report'] = report
        job_store.set_job(job_id, job_info)
        print(f"[{job_id}] Relatório gerado. Job aguardando aprovação do usuário.")
    except Exception as e:
        job_info = get_job(job_id)
        if job_info:
            job_info['status'] = 'failed'
            job_info['error'] = f"Erro ao comunicar com a OpenAI: {e}"
            job_store.set_job(job_id, job_info)
        print(f"ERRO FATAL na geração do relatório [{job_id}]: {e}")

def run_workflow_task(job_id: str):
    try:
        job_info = get_job(job_id)
        print(f"[{job_id}] Iniciando workflow pós-aprovação...")
        
        original_analysis_type = job_info['data']['analysis_type']
        workflow = WORKFLOW_REGISTRY.get(original_analysis_type)
        if not workflow: raise ValueError(f"Nenhum workflow definido para: {original_analysis_type}")
        
        job_info['status'] = 'aplicando_mudancas_do_relatorio'
        job_store.set_job(job_id, job_info)
        print(f"[{job_id}] ... {job_info['status']}")
        
        refactoring_step = workflow['steps'][0]
        agent_params = refactoring_step['params'].copy()
        relatorio_aprovado = job_info['data']['analysis_report']
        instrucoes_iniciais = job_info['data'].get('instrucoes_extras')
        observacoes_aprovacao = job_info['data'].get('observacoes_aprovacao')
        instrucoes_completas = relatorio_aprovado
        if instrucoes_iniciais:
            instrucoes_completas += f"\n\n--- INSTRUÇÕES ADICIONAIS DO USUÁRIO (INICIAL) ---\n{instrucoes_iniciais}"
        if observacoes_aprovacao:
            instrucoes_completas += f"\n\n--- OBSERVAÇÕES DA APROVAÇÃO (APLICAR COM PRIORIDADE) ---\n{observacoes_aprovacao}"
        agent_params.update({'codigo': instrucoes_completas})
        agent_response = refactoring_step['agent_function'](**agent_params)
        json_string_refactor = agent_response['resultado']['reposta_final'].replace("```json", '').replace("```", '')
        resultado_refatoracao = json.loads(json_string_refactor)

        job_info = get_job(job_id)
        job_info['status'] = 'agrupando_mudancas_em_branches'
        job_store.set_job(job_id, job_info)
        print(f"[{job_id}] ... {job_info['status']}")
        
        grouping_step = workflow['steps'][1]
        agent_params_group = grouping_step['params'].copy()
        agent_params_group['codigo'] = str(resultado_refatoracao)
        agent_response_group = grouping_step['agent_function'](**agent_params_group)
        json_string_group = agent_response_group['resultado']['reposta_final'].replace("```json", '').replace("```", '')
        resultado_agrupamento = json.loads(json_string_group)

        job_info = get_job(job_id)
        job_info['status'] = 'preenchendo_dados_para_commit'
        job_store.set_job(job_id, job_info)
        print(f"[{job_id}] ... {job_info['status']}")
        dados_preenchidos = preenchimento.main(json_agrupado=resultado_agrupamento, json_inicial=resultado_refatoracao)
        
        dados_finais_formatados = {"resumo_geral": dados_preenchidos.get("resumo_geral", ""), "grupos": []}
        for nome_grupo, detalhes_pr in dados_preenchidos.items():
            if nome_grupo == "resumo_geral": continue
            dados_finais_formatados["grupos"].append({"branch_sugerida": nome_grupo, "titulo_pr": detalhes_pr.get("resumo_do_pr", ""), "resumo_do_pr": detalhes_pr.get("descricao_do_pr", ""), "conjunto_de_mudancas": detalhes_pr.get("conjunto_de_mudancas", [])})
        
        if not dados_finais_formatados.get("grupos"): raise ValueError("Dados para commit vazios.")

        job_info = get_job(job_id)
        job_info['status'] = 'realizando_commits_no_github'
        job_store.set_job(job_id, job_info)
        print(f"[{job_id}] ... {job_info['status']}")
        
        commit_multiplas_branchs.processar_e_subir_mudancas_agrupadas(
            nome_repo=job_info['data']['repo_name'],
            dados_agrupados=dados_finais_formatados,
            job_id=job_id
        )
        
        job_info = get_job(job_id)
        job_info['status'] = 'completed'
        job_store.set_job(job_id, job_info)
        print(f"[{job_id}] Processo concluído com sucesso!")
        
    except Exception as e:
        job_info_on_error = get_job(job_id)
        if job_info_on_error:
            job_info_on_error['status'] = 'failed'
            job_info_on_error['error'] = str(e)
            job_store.set_job(job_id, job_info_on_error)
        print(f"ERRO FATAL na tarefa de workflow [{job_id}]: {e}")


# --- Endpoints da API ---
@app.post("/jobs/start", response_model=StartJobResponse, tags=["Jobs"])
def start_new_job(payload: StartJobPayload, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    initial_job_data = {'status': 'starting', 'data': {}, 'error': None}
    job_store.set_job(job_id, initial_job_data)
    background_tasks.add_task(run_file_reading_task, job_id, payload)
    return StartJobResponse(job_id=job_id)

@app.post("/jobs/{job_id}/generate_report", tags=["Jobs"])
def generate_report(job_id: str, background_tasks: BackgroundTasks):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")
    if job['status'] != 'files_read_awaits_analysis':
        raise HTTPException(status_code=400, detail=f"O job não está no estado correto. Estado atual: {job['status']}")
    
    background_tasks.add_task(run_report_generation_task, job_id)
    return {"message": "Comando para gerar relatório recebido. Acompanhe o status."}

@app.get("/jobs/status/{job_id}", response_model=JobStatusResponse, tags=["Jobs"])
def get_job_status(job_id: str = Path(..., title="O ID do Job a ser verificado")):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")
    
    return JobStatusResponse(
        job_id=job_id,
        status=job['status'],
        files_read=job['data'].get('files_read'),
        analysis_report=job['data'].get('analysis_report'),
        error_details=job.get('error'),
        commit_links=job['data'].get('commit_links')
    )

@app.post("/update-job-status", tags=["Jobs"])
def update_job_status(payload: UpdateJobPayload, background_tasks: BackgroundTasks):
    job = job_store.get_job(payload.job_id)
    if not job: raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")
    if job['status'] != 'pending_approval': raise HTTPException(status_code=400, detail=f"O job não pode ser modificado. Status atual: {job['status']}")
    
    if payload.action == 'approve':
        if payload.observacoes:
            job['data']['observacoes_aprovacao'] = payload.observacoes
        job['status'] = 'workflow_started'
        job_store.set_job(payload.job_id, job)
        background_tasks.add_task(run_workflow_task, payload.job_id)
        return {"job_id": payload.job_id, "status": "workflow_started", "message": "Processo de refatoração iniciado."}
    
    if payload.action == 'reject':
        job['status'] = 'rejected'
        job_store.set_job(payload.job_id, job)
        return {"job_id": payload.job_id, "status": "rejected", "message": "Processo encerrado a pedido do usuário."}

