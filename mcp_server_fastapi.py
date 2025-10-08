import json
import uuid
import time
import traceback
import os
from urllib.parse import urlparse

from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, Literal, List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware

from services.dependency_container import DependencyContainer
from services.workflow_registry_service import WorkflowRegistryService
from services.api_service_factory import ApiServiceFactory
from services.response_builder_service import FinalStatusResponse
from models import JobStatus, JobFields, JobActions

container = DependencyContainer()
api_service_factory = ApiServiceFactory()
workflow_registry_service = container.get_workflow_registry_service()
ValidAnalysisTypes = workflow_registry_service.get_valid_analysis_types()

response_builder_service = api_service_factory.get_response_builder_service()
repository_normalizer_service = api_service_factory.get_repository_normalizer_service()
job_data_service = api_service_factory.get_job_data_service()
job_validation_service = api_service_factory.get_job_validation_service()
logging_service = api_service_factory.get_logging_service()

class StartAnalysisPayload(BaseModel):
    repo_name_modernizado: str = Field(description="Nome do repositório modernizado")
    branch_name_modernizado: Optional[str] = Field(None, description="Branch do repositório modernizado")
    projeto: str = Field(description="Nome do projeto para agrupar atividades e organizar histórico")
    analysis_type: ValidAnalysisTypes
    instrucoes_extras: Optional[str] = None
    usar_rag: bool = Field(False)
    gerar_relatorio_apenas: bool = Field(False)
    gerar_novo_relatorio: bool = Field(True, description="Se False, tenta ler relatório existente do Blob Storage usando analysis_name")
    model_name: Optional[str] = Field(None, description="Nome do modelo de LLM a ser usado. Se nulo, usa o padrão.")
    arquivos_especificos: Optional[List[str]] = Field(None, description="Lista opcional de caminhos específicos de arquivos para ler. Se fornecido, apenas esses arquivos serão processados.")
    analysis_name: Optional[str] = Field(None, description="Nome personalizado para identificar a análise.")
    repository_type: Literal['github', 'gitlab', 'azure'] = Field(description="Tipo do repositório: 'github', 'gitlab', 'azure'.")
    repo_name_original: Optional[str] = Field(None, description="Nome do repositório original para comparação")
    branch_name_original: Optional[str] = Field(None, description="Branch do repositório original")
    retornar_lista_arquivos: bool = Field(False, description="Se True, além do código filtrado, retorna lista completa de todos os arquivos do repositório")
    modo_adicao_incremental: bool = Field(False, description="Se True, o novo conteúdo será ADICIONADO ao final dos arquivos existentes, ao invés de substituí-los. Útil para migrações de frameworks.")
    usuario_executor: Optional[str] = Field(None, description="Nome do usuário que está executando a análise")
    aplicar_mudancas_incrementalmente: bool = Field(False, description="Se True, ativa o sistema incremental de aplicação de mudanças de código.")

class StartAnalysisResponse(BaseModel):
    job_id: str
    checkpoint_available: bool = Field(False, description="Indica se há checkpoint disponível para retomada da execução incremental.")

class UpdateJobPayload(BaseModel):
    job_id: str
    action: Literal["approve", "reject"]
    instrucoes_extras: Optional[str] = None

class PullRequestSummary(BaseModel):
    pull_request_url: str
    branch_name: str
    arquivos_modificados: List[str]

class ReportResponse(BaseModel):
    job_id: str
    analysis_report: Optional[str]
    report_blob_url: Optional[str] = Field(None)

class AnalysisByNameResponse(BaseModel):
    job_id: str
    analysis_name: str
    analysis_report: Optional[str]
    report_blob_url: Optional[str] = Field(None)

class FinalStatusResponse(BaseModel):
    job_id: str
    status: str
    summary: Optional[List[PullRequestSummary]] = None
    error_details: Optional[str] = None
    analysis_report: Optional[str] = None
    diagnostic_logs: Optional[Dict[str, Any]] = None
    report_blob_url: Optional[str] = None
    incremental_execution_summary: Optional[Dict[str, Any]] = None

app = FastAPI(
    title="MCP Server - Multi-Agent Code Platform",
    description="Servidor robusto com Redis para orquestrar agentes de IA.",
    version="9.0.0" 
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def run_workflow_task(job_id: str, start_from_step: int = 0):
    workflow_orchestrator = container.get_workflow_orchestrator()
    workflow_orchestrator.execute_workflow(job_id, start_from_step)

@app.post("/start-analysis", response_model=StartAnalysisResponse, tags=["Jobs"])
def start_analysis(payload: StartAnalysisPayload, background_tasks: BackgroundTasks):
    job_store = container.get_job_store()
    analysis_service = container.get_analysis_name_service()
    repo_name = payload.repo_name_modernizado
    branch_name = payload.branch_name_modernizado
    normalized_repo_name = repository_normalizer_service.normalize_repo_name(
        repo_name, payload.repository_type
    )
    job_id = str(uuid.uuid4())
    analysis_name = job_data_service.generate_analysis_name(payload.analysis_name, job_id)
    payload_dict = payload.dict()
    payload_dict['analysis_type'] = payload.analysis_type.value
    if payload_dict.get('aplicar_mudancas_incrementalmente', False):
        if payload_dict.get('gerar_relatorio_apenas', False):
            raise HTTPException(status_code=400, detail="Não é permitido ativar 'aplicar_mudancas_incrementalmente' quando 'gerar_relatorio_apenas' está ativo.")
    initial_job_data = job_data_service.create_initial_job_data(
        payload_dict, normalized_repo_name, analysis_name
    )
    job_store.set_job(job_id, initial_job_data)
    logging_service.log_starting_job(job_id, payload_dict, normalized_repo_name, analysis_name)
    if analysis_name:
        analysis_service.register_analysis(analysis_name, job_id)
    print(f"[{job_id}] Job criado - Repositório: '{normalized_repo_name}' (tipo: {payload.repository_type}), Projeto: '{payload.projeto}'")
    background_tasks.add_task(run_workflow_task, job_id, start_from_step=0)
    incremental_orchestrator_service = container.get_incremental_orchestrator_service()
    checkpoint_available = False
    checkpoint = incremental_orchestrator_service.get_checkpoint(job_id)
    if checkpoint and checkpoint.get('completed_tasks'):
        checkpoint_available = True
    return StartAnalysisResponse(job_id=job_id, checkpoint_available=checkpoint_available)

@app.post("/resume-incremental-changes/{job_id}", response_model=Dict[str, Any], tags=["Jobs"])
def resume_incremental_changes(job_id: str, background_tasks: BackgroundTasks):
    job_store = container.get_job_store()
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get(JobFields.STATUS) != "incremental_execution_paused":
        raise HTTPException(status_code=400, detail="Job não está em estado de pausa incremental")
    incremental_orchestrator_service = container.get_incremental_orchestrator_service()
    checkpoint = incremental_orchestrator_service.get_checkpoint(job_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint não encontrado para este job")
    completed_task_ids = checkpoint.get('completed_tasks', [])
    report_text = job.get(JobFields.DATA, {}).get(JobFields.ANALYSIS_REPORT)
    repo_name = job.get(JobFields.DATA, {}).get(JobFields.REPO_NAME)
    branch_name = job.get(JobFields.DATA, {}).get(JobFields.BRANCH_NAME)
    repository_type = job.get(JobFields.DATA, {}).get(JobFields.REPOSITORY_TYPE)
    result = incremental_orchestrator_service.execute_incremental_changes(
        job_id=job_id,
        report_text=report_text,
        repo_name=repo_name,
        branch_name=branch_name,
        repository_type=repository_type,
        completed_task_ids=completed_task_ids
    )
    job[JobFields.DATA]['incremental_execution_summary'] = result
    job_store.set_job(job_id, job)
    return result
