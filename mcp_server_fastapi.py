import json
import uuid
import yaml
import time
import traceback
import enum
from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, Literal, List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware

from tools.job_store import RedisJobStore
from services.workflow_orchestrator import WorkflowOrchestrator
from services.job_manager import JobManager
from services.blob_storage_service import BlobStorageService

def load_workflow_registry(filepath: str) -> dict:
    print(f"Carregando workflows do arquivo: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

WORKFLOW_REGISTRY = load_workflow_registry("workflows.yaml")
valid_analysis_keys = {key: key for key in WORKFLOW_REGISTRY.keys()}
ValidAnalysisTypes = enum.Enum('ValidAnalysisTypes', valid_analysis_keys)

def _validate_and_normalize_gitlab_repo_name(repo_name: str) -> str:
    repo_name = repo_name.strip()
    
    try:
        project_id = int(repo_name)
        print(f"GitLab Project ID detectado: {project_id}. Usando formato numérico para máxima robustez.")
        return str(project_id)
    except ValueError:
        pass
    
    if '/' in repo_name:
        parts = repo_name.split('/')
        if len(parts) >= 2:
            print(f"GitLab path completo detectado: {repo_name}. RECOMENDAÇÃO: Use o Project ID numérico para máxima robustez contra renomeações.")
            return repo_name
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Path GitLab inválido: '{repo_name}'. Esperado pelo menos 'namespace/projeto'. Exemplo: 'meugrupo/meuprojeto' ou use o Project ID numérico (recomendado)."
            )
    
    raise HTTPException(
        status_code=400,
        detail=f"Formato de repositório GitLab inválido: '{repo_name}'. Use o Project ID numérico (RECOMENDADO para máxima robustez) ou o path completo 'namespace/projeto'. Exemplos: Project ID: '123456', Path: 'meugrupo/meuprojeto'"
    )

def _normalize_repo_name_by_type(repo_name: str, repository_type: str) -> str:
    """Normaliza o nome do repositório baseado no tipo."""
    if repository_type == 'gitlab':
        normalized = _validate_and_normalize_gitlab_repo_name(repo_name)
        print(f"GitLab - Repo original: '{repo_name}', normalizado: '{normalized}'")
        return normalized
    return repo_name

def _generate_analysis_name(provided_name: Optional[str], job_id: str) -> str:
    """Gera ou valida o nome da análise."""
    if provided_name:
        return provided_name
    
    analysis_name = f"analysis-{str(uuid.uuid4())[:8]}"
    print(f"[{job_id}] Nome de análise gerado automaticamente: {analysis_name}")
    return analysis_name

def _create_initial_job_data(payload: StartAnalysisPayload, normalized_repo_name: str, analysis_name: str) -> dict:
    """Cria a estrutura inicial de dados do job."""
    return {
        'status': 'starting',
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

def _validate_job_for_approval(job: dict, job_id: str) -> None:
    """Valida se o job está em estado válido para aprovação."""
    if not job or job.get('status') != 'pending_approval':
        raise HTTPException(status_code=400, detail="Job não encontrado ou não está aguardando aprovação.")

def _validate_job_exists(job: dict, job_id: str) -> None:
    """Valida se o job existe."""
    if not job:
        raise HTTPException(status_code=404, detail="Job ID não encontrado ou expirado")

def _validate_analysis_exists(analysis_name: str) -> str:
    """Valida se a análise existe e retorna o job_id."""
    job_id = analysis_name_to_job_id.get(analysis_name)
    if not job_id:
        raise HTTPException(status_code=404, detail=f"Análise com nome '{analysis_name}' não encontrada")
    return job_id

def _get_report_from_job(job: dict, job_id: str) -> str:
    """Extrai o relatório do job ou levanta exceção se não encontrado."""
    report = job.get("data", {}).get("analysis_report")
    if not report:
        if job_id:
            raise HTTPException(status_code=404, detail=f"Relatório não encontrado para este job. Status: {job.get('status')}")
        else:
            raise HTTPException(status_code=404, detail="Relatório não encontrado no job original")
    return report

def _create_derived_job_data(original_job: dict, analysis_name: str, normalized_repo_name: str, report: str) -> dict:
    """Cria dados para job derivado de implementação."""
    return {
        'status': 'starting',
        'data': {
            'repo_name': normalized_repo_name,
            'original_repo_name': original_job['data']['repo_name'],
            'projeto': original_job['data']['projeto'],
            'branch_name': original_job['data']['branch_name'],
            'original_analysis_type': 'implementacao',
            'instrucoes_extras': f"Gerar código baseado no seguinte relatório:\n\n{report}",
            'model_name': original_job['data'].get('model_name'),
            'usar_rag': original_job['data'].get('usar_rag', False),
            'gerar_relatorio_apenas': False,
            'gerar_novo_relatorio': True,
            'arquivos_especificos': original_job['data'].get('arquivos_especificos'),
            'analysis_name': f"{analysis_name}-implementation",
            'repository_type': original_job['data']['repository_type']
        },
        'error_details': None
    }

def _build_completed_response(job_id: str, job: dict, blob_url: Optional[str]) -> FinalStatusResponse:
    """Constrói resposta para jobs completados."""
    if job.get("data", {}).get("gerar_relatorio_apenas") is True:
        return FinalStatusResponse(
            job_id=job_id,
            status='completed',
            analysis_report=job.get("data", {}).get("analysis_report"),
            report_blob_url=blob_url
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
        logs = job.get("data", {}).get("diagnostic_logs")
        return FinalStatusResponse(
            job_id=job_id, 
            status='completed', 
            summary=summary_list,
            diagnostic_logs=logs,
            report_blob_url=blob_url
        )

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
    normalized_repo_name = _normalize_repo_name_by_type(payload.repo_name, payload.repository_type)
    
    job_id = str(uuid.uuid4())
    analysis_name = _generate_analysis_name(payload.analysis_name, job_id)
    
    initial_job_data = _create_initial_job_data(payload, normalized_repo_name, analysis_name)
    
    job_store.set_job(job_id, initial_job_data)
    
    if analysis_name:
        analysis_name_to_job_id[analysis_name] = job_id
    
    print(f"[{job_id}] Job criado - Repositório: '{normalized_repo_name}' (tipo: {payload.repository_type}), Projeto: '{payload.projeto}'")
    
    background_tasks.add_task(run_workflow_task, job_id, start_from_step=0)
    
    return StartAnalysisResponse(job_id=job_id)
    
@app.post("/update-job-status", response_model=Dict[str, str], tags=["Jobs"])
def update_job_status(payload: UpdateJobPayload, background_tasks: BackgroundTasks):
    job = job_store.get_job(payload.job_id)
    _validate_job_for_approval(job, payload.job_id)
    
    if payload.action == 'approve':
        job['data']['instrucoes_extras_aprovacao'] = payload.instrucoes_extras
        job['status'] = 'workflow_started'
        
        paused_step = job['data'].get('paused_at_step', 0)
        start_from_step = paused_step + 1
        
        job_store.set_job(payload.job_id, job)
        
        background_tasks.add_task(run_workflow_task, payload.job_id, start_from_step=start_from_step)
        
        return {"job_id": payload.job_id, "status": "workflow_started", "message": "Aprovação recebida."}
    
    if payload.action == 'reject':
        job['status'] = 'rejected'
        job_store.set_job(payload.job_id, job)
        return {"job_id": payload.job_id, "status": "rejected", "message": "Processo encerrado."}

@app.get("/jobs/{job_id}/report", response_model=ReportResponse, tags=["Jobs"])
def get_job_report(job_id: str = Path(..., title="O ID do Job para buscar o relatório")):
    job = job_store.get_job(job_id)
    _validate_job_exists(job, job_id)
    
    report = _get_report_from_job(job, job_id)
    blob_url = job.get("data", {}).get("report_blob_url")
    
    return ReportResponse(job_id=job_id, analysis_report=report, report_blob_url=blob_url)

@app.get("/analyses/by-name/{analysis_name}", response_model=AnalysisByNameResponse, tags=["Jobs"])
def get_analysis_by_name(analysis_name: str = Path(..., title="Nome da análise para buscar")):
    job_id = _validate_analysis_exists(analysis_name)
    
    job = job_store.get_job(job_id)
    _validate_job_exists(job, job_id)
    
    report = job.get("data", {}).get("analysis_report")
    blob_url = job.get("data", {}).get("report_blob_url")
    
    return AnalysisByNameResponse(
        job_id=job_id,
        analysis_name=analysis_name,
        analysis_report=report,
        report_blob_url=blob_url
    )

@app.post("/start-code-generation-from-report/{analysis_name}", response_model=StartAnalysisResponse, tags=["Jobs"])
def start_code_generation_from_report(analysis_name: str, background_tasks: BackgroundTasks):
    job_id = _validate_analysis_exists(analysis_name)
    
    original_job = job_store.get_job(job_id)
    _validate_job_exists(original_job, job_id)
    
    report = _get_report_from_job(original_job, None)
    
    original_repo_name = original_job['data']['repo_name']
    original_repository_type = original_job['data']['repository_type']
    
    normalized_repo_name = _normalize_repo_name_by_type(original_repo_name, original_repository_type)
    
    new_job_id = str(uuid.uuid4())
    
    new_job_data = _create_derived_job_data(original_job, analysis_name, normalized_repo_name, report)
    
    job_store.set_job(new_job_id, new_job_data)
    analysis_name_to_job_id[f"{analysis_name}-implementation"] = new_job_id
    
    print(f"[{new_job_id}] Job derivado criado - Repositório: '{normalized_repo_name}' (tipo: {original_repository_type}), Projeto: '{original_job['data']['projeto']}'")
    
    background_tasks.add_task(run_workflow_task, new_job_id, start_from_step=0)
    
    return StartAnalysisResponse(job_id=new_job_id)

@app.get("/status/{job_id}", response_model=FinalStatusResponse, tags=["Jobs"])
def get_status(job_id: str = Path(..., title="O ID do Job a ser verificado")):
    job = job_store.get_job(job_id)
    _validate_job_exists(job, job_id)

    status = job.get('status')
    blob_url = job.get("data", {}).get("report_blob_url")

    try:
        if status == 'completed':
            return _build_completed_response(job_id, job, blob_url)
        elif status == 'failed':
            logs = job.get("data", {}).get("diagnostic_logs")
            return FinalStatusResponse(
                job_id=job_id,
                status=status,
                error_details=job.get("error_details", "Nenhum detalhe de erro encontrado."),
                diagnostic_logs=logs,
                report_blob_url=blob_url
            )
        else:
            return FinalStatusResponse(job_id=job_id, status=status, report_blob_url=blob_url)
    except ValidationError as e:
        print(f"ERRO CRÍTICO de Validação no Job ID {job_id}: {e}")
        print(f"Dados brutos do job que causaram o erro: {job}")
        raise HTTPException(status_code=500, detail="Erro interno ao formatar a resposta do status do job.")