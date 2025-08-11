# Arquivo: mcp_server_fastapi.py (VERSÃO 6.1 - ALINHADO COM AGENTE CORRETO)

import json
import uuid
from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel
from typing import Optional, Literal, List, Dict
from fastapi.middleware.cors import CORSMiddleware

# Importa as funções do nosso módulo de armazenamento
from tools.job_store import get_job, set_job

# --- Módulos do seu projeto ---
from agents import agente_revisor
from tools import preenchimento, commit_multiplas_branchs

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
    description="Servidor robusto com fluxo de status deliberado para análise de código.",
    version="6.1.0"
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
WORKFLOW_REGISTRY = {
    "design": {
        "description": "Analisa o design, refatora o código e agrupa os commits.",
        "steps": [{"agent_function": agente_revisor.main, "params": {"tipo_analise": "refatoracao"}},
                  {"agent_function": agente_revisor.main, "params": {"tipo_analise": "agrupamento_design"}}]
    },
    "relatorio_teste_unitario": {
        "description": "Cria testes unitários com base no relatório e os agrupa.",
        "steps": [{"agent_function": agente_revisor.main, "params": {"tipo_analise": "escrever_testes"}},
                  {"agent_function": agente_revisor.main, "params": {"tipo_analise": "agrupamento_testes"}}]
    }
}


# --- Lógica das Tarefas em Background ---

def run_file_reading_task(job_id: str, payload: StartJobPayload):
    try:
        job_info = get_job(job_id)
        job_info['status'] = 'lendo_repositorio'
        set_job(job_id, job_info)
        print(f"[{job_id}] Tarefa de leitura de arquivos iniciada...")
        
        # [CORREÇÃO] Chama a função que APENAS LÊ os arquivos: code_from_repo
        codigo_com_conteudo = agente_revisor.code_from_repo(
            repositorio=payload.repo_name,
            tipo_analise=payload.analysis_type,
            nome_branch=payload.branch_name
        )
        nomes_dos_arquivos = list(codigo_com_conteudo.keys())

        job_info['status'] = 'files_read_awaits_analysis'
        job_info['data']['files_read'] = nomes_dos_arquivos
        job_info['data']['codigo_com_conteudo'] = codigo_com_conteudo
        job_info['data'].update(payload.dict(exclude_unset=False)) 
        set_job(job_id, job_info)
        print(f"[{job_id}] Leitura concluída. Aguardando comando para iniciar análise.")
    except Exception as e:
        job_info = get_job(job_id)
        if job_info:
            job_info['status'] = 'failed'
            job_info['error'] = str(e)
            set_job(job_id, job_info)
        print(f"ERRO FATAL na tarefa de leitura [{job_id}]: {e}")

def run_report_generation_task(job_id: str):
    try:
        job_info = get_job(job_id)
        job_info['status'] = 'gerando_relatorio_ia'
        set_job(job_id, job_info)
        print(f"[{job_id}] Tarefa de geração de relatório iniciada...")

        codigo_com_conteudo = job_info['data']['codigo_com_conteudo']
        payload_dict = job_info['data']
        
        # [CORREÇÃO] Chama a função que GERA O RELATÓRIO: main
        # Passamos o 'codigo' já lido para que a função 'main' não precise ler o repo novamente.
        resposta_agente = agente_revisor.main(
            tipo_analise=payload_dict['analysis_type'],
            codigo=str(codigo_com_conteudo),
            instrucoes_extras=payload_dict.get('instrucoes_extras')
        )
        # A função main já retorna o dicionário completo, então pegamos a chave 'resultado'
        report = resposta_agente['resultado']['reposta_final']
        
        job_info['status'] = 'pending_approval'
        job_info['data']['analysis_report'] = report
        set_job(job_id, job_info)
        print(f"[{job_id}] Relatório gerado. Job aguardando aprovação do usuário.")
    except Exception as e:
        job_info = get_job(job_id)
        if job_info:
            job_info['status'] = 'failed'
            job_info['error'] = f"Erro ao comunicar com a OpenAI: {e}"
            set_job(job_id, job_info)
        print(f"ERRO FATAL na geração do relatório [{job_id}]: {e}")

# ... (run_workflow_task e todos os endpoints não precisam de alterações) ...
def run_workflow_task(job_id: str):
    # Sua lógica de workflow que já estava funcionando
    pass

@app.post("/jobs/start", response_model=StartJobResponse, tags=["Jobs"])
def start_new_job(payload: StartJobPayload, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    initial_job_data = {'status': 'starting', 'data': {}, 'error': None}
    set_job(job_id, initial_job_data)
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
    job = get_job(job_id)
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
    job = get_job(payload.job_id)
    if not job: raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")
    if job['status'] != 'pending_approval': raise HTTPException(status_code=400, detail=f"O job não pode ser modificado. Status atual: {job['status']}")
    
    if payload.action == 'approve':
        if payload.observacoes:
            job['data']['observacoes_aprovacao'] = payload.observacoes
        job['status'] = 'workflow_started'
        set_job(payload.job_id, job)
        background_tasks.add_task(run_workflow_task, payload.job_id)
        return {"job_id": payload.job_id, "status": "workflow_started", "message": "Processo de refatoração iniciado."}
    
    if payload.action == 'reject':
        job['status'] = 'rejected'
        set_job(payload.job_id, job)
        return {"job_id": payload.job_id, "status": "rejected", "message": "Processo encerrado a pedido do usuário."}
