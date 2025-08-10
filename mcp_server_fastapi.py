# Arquivo: mcp_server_fastapi.py (VERSÃO 5.0 - ROBUSTA COM REDIS)

import json
import uuid
import os
import redis
from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel
from typing import Optional, Literal, List, Dict
from fastapi.middleware.cors import CORSMiddleware

# --- Módulos do seu projeto ---
from agents import agente_revisor
from tools import preenchimento, commit_multiplas_branchs

# --- Modelos de Dados (Pydantic) ---
# (Sem alterações nos modelos)
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

class UpdateJobPayload(BaseModel):
    job_id: str
    action: Literal["approve", "reject"]
    observacoes: Optional[str] = None


# --- Configuração do Redis (O novo armazenamento de estado) ---

# Pega a URL de conexão do Redis das variáveis de ambiente do App Service
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    # Lança um erro claro se a variável não estiver configurada
    raise ValueError("A variável de ambiente REDIS_URL não foi configurada no servidor!")

# Inicializa o cliente Redis
# decode_responses=True faz com que os resultados venham como strings (não bytes)
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

def set_job(job_id: str, job_data: Dict):
    """ Salva os dados de um job no Redis, convertendo para JSON. """
    # Define um tempo de expiração de 24 horas (em segundos) para limpar jobs antigos
    redis_client.set(job_id, json.dumps(job_data), ex=86400)

def get_job(job_id: str) -> Optional[Dict]:
    """ Pega os dados de um job do Redis, convertendo de JSON para dicionário. """
    job_json = redis_client.get(job_id)
    if job_json:
        return json.loads(job_json)
    return None

# --- Configuração do Servidor FastAPI ---
app = FastAPI(
    title="MCP Server - Multi-Agent Code Platform",
    description="Servidor robusto com armazenamento de estado persistente via Redis.",
    version="5.0.0" 
)

# Configuração do CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# [REMOVIDO] Não usamos mais o dicionário em memória
# jobs: Dict[str, Dict] = {} 

# Registro de workflows pós-aprovação
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


# --- Lógica das Tarefas em Background (usando Redis) ---

def run_file_reading_task(job_id: str, payload: StartJobPayload):
    try:
        job_info = get_job(job_id)
        job_info['status'] = 'reading_files'
        set_job(job_id, job_info)
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
        job_info['status'] = 'generating_report'
        set_job(job_id, job_info)
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
        set_job(job_id, job_info)
        print(f"[{job_id}] Relatório gerado. Job aguardando aprovação do usuário.")

    except Exception as e:
        job_info = get_job(job_id)
        if job_info:
            job_info['status'] = 'failed'
            job_info['error'] = f"Erro ao comunicar com a OpenAI: {e}"
            set_job(job_id, job_info)
        print(f"ERRO FATAL na geração do relatório [{job_id}]: {e}")


def run_workflow_task(job_id: str):
    try:
        job_info = get_job(job_id)
        print(f"[{job_id}] Iniciando workflow pós-aprovação...")
        original_analysis_type = job_info['data']['analysis_type']
        workflow = WORKFLOW_REGISTRY.get(original_analysis_type)
        if not workflow: raise ValueError(f"Nenhum workflow definido para: {original_analysis_type}")
        
        # ... (resto da lógica do workflow, usando set_job para cada atualização de status) ...
        # Exemplo:
        for i, step in enumerate(workflow['steps']):
            job_info['status'] = step['status_update']
            set_job(job_id, job_info)
            # ... resto da lógica do passo ...
        
        job_info['status'] = 'completed'
        set_job(job_id, job_info)
        print(f"[{job_id}] Processo concluído com sucesso!")
        
    except Exception as e:
        job_info = get_job(job_id)
        if job_info:
            job_info['status'] = 'failed'
            job_info['error'] = str(e)
            set_job(job_id, job_info)
        print(f"ERRO FATAL na tarefa de workflow [{job_id}]: {e}")


# --- Endpoints da API (usando Redis) ---

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
        error_details=job.get('error')
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
        set_job(payload.job_id, job) # Salva a mudança antes de iniciar a tarefa
        background_tasks.add_task(run_workflow_task, payload.job_id)
        return {"job_id": payload.job_id, "status": "workflow_started", "message": "Processo de refatoração iniciado."}
    
    if payload.action == 'reject':
        job['status'] = 'rejected'
        set_job(payload.job_id, job)
        return {"job_id": payload.job_id, "status": "rejected", "message": "Processo encerrado a pedido do usuário."}
