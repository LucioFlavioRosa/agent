import json
import uuid
import yaml
import time
import traceback

from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, Literal, List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware

from tools.job_store import RedisJobStore
from services.workflow_orchestrator import WorkflowOrchestrator
from services.job_manager import JobManager
from services.blob_storage_service import BlobStorageService

# Status simples de Jobs
JOB_STATUS_STARTING = 'starting'
JOB_STATUS_PENDING_APPROVAL = 'pending_approval'
JOB_STATUS_WORKFLOW_STARTED = 'workflow_started'
JOB_STATUS_COMPLETED = 'completed'
JOB_STATUS_FAILED = 'failed'
JOB_STATUS_REJECTED = 'rejected'

# Actions simples
JOB_ACTION_APPROVE = 'approve'
JOB_ACTION_REJECT = 'reject'

def load_workflow_registry(filepath: str) -> dict:
    print(f"Carregando workflows do arquivo: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

WORKFLOW_REGISTRY = load_workflow_registry("workflows.yaml")

# Enum simples para tipos de análise
from enum import Enum
ValidAnalysisTypes = Enum('ValidAnalysisTypes', {key: key for key in WORKFLOW_REGISTRY.keys()})

class StartAnalysisPayload(BaseModel):
    repo_name: str
    projeto: str = Field(description="Nome do projeto para agrupar atividades e organizar histórico")
    analysis_type: ValidAnalysisTypes
    branch_name: Optional[str] = None
    instrucoes_extras: Optional[str] = None
    usar_rag: bool = Field(False)
    gerar_relatorio_apenas: bool = Field(False)
    gerar_novo_relatorio: bool = Field(True, description="Se False, tenta ler relatório existente do Blob Storage usando analysis_name")
    model_name: Optional[str] = Field(None, description="Nome do modelo de LLM a ser usado. Se nulo, usa o padrão.")
    arquivos_especificos: Optional[List[str]] = Field(None, description="Lista opcional de caminhos específicos de arquivos para ler. Se fornecido, apenas esses arquivos serão processados.")
    analysis_name: Optional[str] = Field(None, description="Nome personalizado para identificar a análise.")
    repository_type: Literal['github', 'gitlab', 'azure'] = Field(description="Tipo do repositório: 'github', 'gitlab', 'azure'.")

class StartAnalysisResponse(BaseModel):
    job_id: str

class UpdateJobPayload(BaseModel):
    job_id: str
    action: Literal["approve", "reject"]
    instrucoes_extras: Optional[str] = None

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
    report_blob_url: Optional[str] = Field(None)

class ReportResponse(BaseModel):
    job_id: str
    analysis_report: Optional[str]
    report_blob_url: Optional[str] = Field(None)

class AnalysisByNameResponse(BaseModel):
    job_id: str
    analysis_name: str
    analysis_report: Optional[str]
    report_blob_url: Optional[str] = Field(None)

def validate_gitlab_repo_name(repo_name: str) -> str:
    """Valida e normaliza nome de repositório GitLab"""
    repo_name = repo_name.strip()
    
    # Tenta converter para ID numérico
    try:
        project_id = int(repo_name)
        print(f"GitLab Project ID detectado: {project_id}")
        return str(project_id)
    except ValueError:
        pass
    
    # Valida formato path
    if '/' in repo_name and len(repo_name.split('/')) >= 2:
        print(f"GitLab path detectado: {repo_name}")
        return repo_name
    
    raise HTTPException(
        status_code=400,
        detail=f"Formato GitLab inválido: '{repo_name}'. Use Project ID numérico ou 'namespace/projeto'"
    )

def normalize_repo_name(repo_name: str, repository_type: str) -> str:
    """Normaliza nome do repositório baseado no tipo"""
    if repository_type == 'gitlab':
        return validate_gitlab_repo_name(repo_name)
    return repo_name

def generate_analysis_name(provided_name: Optional[str], job_id: str) -> str:
    """Gera nome da análise se não fornecido"""
    if provided_name:
        return provided_name
    
    analysis_name = f"analysis-{str(uuid.uuid4())[:8]}"
    print(f"[{job_id}] Nome gerado: {analysis_name}")
    return analysis_name

def create_job_data(payload: StartAnalysisPayload, normalized_repo_name: str, analysis_name: str) -> dict:
    """Cria estrutura de dados do job"""
    return {
        'status': JOB_STATUS_STARTING,
        'data': {
            'repo_name': normalized_repo_name,
            'original_repo_name': payload.repo_name,
            'projeto': payload.projeto,
            'branch_name': payload.branch_name,
            'original_analysis_type': payload.analysis_type.value,
            'instrucoes_extras': payload.instrucoes_extras,
            'model_name': payload.model_name,
            'usar_rag': payload.usar_rag,
            'gerar_relatorio_apenas': payload.gerar_relatorio_apenas,
            'gerar_novo_relatorio': payload.gerar_novo_relatorio,
            'arquivos_especificos': payload.arquivos_especificos,
            'analysis_name': analysis_name,
            'repository_type': payload.repository_type
        },
        'error_details': None
    }

def build_completed_response(job_id: str, job: dict, blob_url: Optional[str]) -> FinalStatusResponse:
    """Constrói resposta para jobs completados"""
    job_data = job.get('data', {})
    
    if job_data.get('gerar_relatorio_apenas') is True:
        return FinalStatusResponse(
            job_id=job_id,
            status=JOB_STATUS_COMPLETED,
            analysis_report=job_data.get('analysis_report'),
            report_blob_url=blob_url
        )
    
    # Constrói lista de PRs
    summary_list = []
    commit_details = job_data.get('commit_details', [])
    for pr_info in commit_details:
        if pr_info.get('success') and pr_info.get('pr_url'):
            summary_list.append(
                PullRequestSummary(
                    pull_request_url=pr_info.get('pr_url'),
                    branch_name=pr_info.get('branch_name'),
                    arquivos_modificados=pr_info.get('arquivos_modificados', [])
                )
            )
    
    return FinalStatusResponse(
        job_id=job_id, 
        status=JOB_STATUS_COMPLETED, 
        summary=summary_list,
        diagnostic_logs=job_data.get('diagnostic_logs'),
        report_blob_url=blob_url
    )

app = FastAPI(
    title="MCP Server - Multi-Agent Code Platform",
    description="Servidor robusto com Redis para orquestrar agentes de IA.",
    version="9.0.0" 
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

job_store = RedisJobStore()
job_manager = JobManager(job_store)
blob_storage = BlobStorageService()
workflow_orchestrator = WorkflowOrchestrator(job_manager, blob_storage, WORKFLOW_REGISTRY)
analysis_name_to_job_id = {}

def run_workflow_task(job_id: str, start_from_step: int = 0):
    workflow_orchestrator.execute_workflow(job_id, start_from_step)

@app.post("/start-analysis", response_model=StartAnalysisResponse, tags=["Jobs"])
def start_analysis(payload: StartAnalysisPayload, background_tasks: BackgroundTasks):
    normalized_repo_name = normalize_repo_name(payload.repo_name, payload.repository_type)
    
    job_id = str(uuid.uuid4())
    analysis_name = generate_analysis_name(payload.analysis_name, job_id)
    
    job_data = create_job_data(payload, normalized_repo_name, analysis_name)
    
    job_store.set_job(job_id, job_data)
    
    if analysis_name:
        analysis_name_to_job_id[analysis_name] = job_id
    
    print(f"[{job_id}] Job criado - Repo: '{normalized_repo_name}' (tipo: {payload.repository_type}), Projeto: '{payload.projeto}'")
    
    background_tasks.add_task(run_workflow_task, job_id, start_from_step=0)
    
    return StartAnalysisResponse(job_id=job_id)
    
@app.post("/update-job-status", response_model=Dict[str, str], tags=["Jobs"])
def update_job_status(payload: UpdateJobPayload, background_tasks: BackgroundTasks):
    job = job_store.get_job(payload.job_id)
    
    if not job or job.get('status') != JOB_STATUS_PENDING_APPROVAL:
        raise HTTPException(status_code=400, detail="Job não encontrado ou não está aguardando aprovação.")
    
    if payload.action == JOB_ACTION_APPROVE:
        job['data']['instrucoes_extras_aprovacao'] = payload.instrucoes_extras
        job['status'] = JOB_STATUS_WORKFLOW_STARTED
        
        paused_step = job['data'].get('paused_at_step', 0)
        start_from_step = paused_step + 1
        
        job_store.set_job(payload.job_id, job)
        
        background_tasks.add_task(run_workflow_task, payload.job_id, start_from_step=start_from_step)
        
        return {"job_id": payload.job_id, "status": JOB_STATUS_WORKFLOW_STARTED, "message": "Aprovação recebida."}
    
    if payload.action == JOB_ACTION_REJECT:
        job['status'] = JOB_STATUS_REJECTED
        job_store.set_job(payload.job_id, job)
        return {"job_id": payload.job_id, "status": JOB_STATUS_REJECTED, "message": "Processo encerrado."}

@app.get("/jobs/{job_id}/report", response_model=ReportResponse, tags=["Jobs"])
def get_job_report(job_id: str = Path(..., title="O ID do Job para buscar o relatório")):
    job = job_store.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")
    
    report = job.get('data', {}).get('analysis_report')
    if not report:
        raise HTTPException(status_code=404, detail=f"Relatório não encontrado para este job. Status: {job.get('status')}")
    
    blob_url = job.get('data', {}).get('report_blob_url')
    
    return ReportResponse(job_id=job_id, analysis_report=report, report_blob_url=blob_url)

@app.get("/analyses/by-name/{analysis_name}", response_model=AnalysisByNameResponse, tags=["Jobs"])
def get_analysis_by_name(analysis_name: str = Path(..., title="Nome da análise para buscar")):
    job_id = analysis_name_to_job_id.get(analysis_name)
    if not job_id:
        raise HTTPException(status_code=404, detail=f"Análise com nome '{analysis_name}' não encontrada")
    
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")
    
    report = job.get('data', {}).get('analysis_report')
    blob_url = job.get('data', {}).get('report_blob_url')
    
    return AnalysisByNameResponse(
        job_id=job_id,
        analysis_name=analysis_name,
        analysis_report=report,
        report_blob_url=blob_url
    )

@app.post("/start-code-generation-from-report/{analysis_name}", response_model=StartAnalysisResponse, tags=["Jobs"])
def start_code_generation_from_report(analysis_name: str, background_tasks: BackgroundTasks):
    job_id = analysis_name_to_job_id.get(analysis_name)
    if not job_id:
        raise HTTPException(status_code=404, detail=f"Análise com nome '{analysis_name}' não encontrada")
    
    original_job = job_store.get_job(job_id)
    if not original_job:
        raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")
    
    report = original_job.get('data', {}).get('analysis_report')
    if not report:
        raise HTTPException(status_code=404, detail="Relatório não encontrado no job original")
    
    original_data = original_job['data']
    original_repo_name = original_data['repo_name']
    original_repository_type = original_data['repository_type']
    
    normalized_repo_name = normalize_repo_name(original_repo_name, original_repository_type)
    
    new_job_id = str(uuid.uuid4())
    
    # Cria job derivado simples
    new_job_data = {
        'status': JOB_STATUS_STARTING,
        'data': {
            'repo_name': normalized_repo_name,
            'original_repo_name': original_data['repo_name'],
            'projeto': original_data['projeto'],
            'branch_name': original_data['branch_name'],
            'original_analysis_type': 'implementacao',
            'instrucoes_extras': f"Gerar código baseado no seguinte relatório:\n\n{report}",
            'model_name': original_data.get('model_name'),
            'usar_rag': original_data.get('usar_rag', False),
            'gerar_relatorio_apenas': False,
            'gerar_novo_relatorio': True,
            'arquivos_especificos': original_data.get('arquivos_especificos'),
            'analysis_name': f"{analysis_name}-implementation",
            'repository_type': original_data['repository_type']
        },
        'error_details': None
    }
    
    job_store.set_job(new_job_id, new_job_data)
    analysis_name_to_job_id[f"{analysis_name}-implementation"] = new_job_id
    
    print(f"[{new_job_id}] Job derivado criado - Repo: '{normalized_repo_name}' (tipo: {original_repository_type}), Projeto: '{original_data['projeto']}'")
    
    background_tasks.add_task(run_workflow_task, new_job_id, start_from_step=0)
    
    return StartAnalysisResponse(job_id=new_job_id)

@app.get("/status/{job_id}", response_model=FinalStatusResponse, tags=["Jobs"])
def get_status(job_id: str = Path(..., title="O ID do Job a ser verificado")):
    job = job_store.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")

    status = job.get('status')
    blob_url = job.get('data', {}).get('report_blob_url')

    try:
        if status == JOB_STATUS_COMPLETED:
            return build_completed_response(job_id, job, blob_url)
        elif status == JOB_STATUS_FAILED:
            logs = job.get('data', {}).get('diagnostic_logs')
            return FinalStatusResponse(
                job_id=job_id,
                status=status,
                error_details=job.get('error_details', "Nenhum detalhe de erro encontrado."),
                diagnostic_logs=logs,
                report_blob_url=blob_url
            )
        else:
            return FinalStatusResponse(job_id=job_id, status=status, report_blob_url=blob_url)
    except ValidationError as e:
        print(f"ERRO CRÍTICO de Validação no Job ID {job_id}: {e}")
        print(f"Dados brutos do job que causaram o erro: {job}")
        raise HTTPException(status_code=500, detail="Erro interno ao formatar a resposta do status do job.")