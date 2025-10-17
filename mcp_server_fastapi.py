import json
import uuid
import time
import traceback
import os
from typing import Optional

from urllib.parse import urlparse
from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, Literal, List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware
from services.dependency_container import DependencyContainer
from services.workflow_registry_service import WorkflowRegistryService
from services.api_service_factory import ApiServiceFactory
from services.pull_request_extractor_service import PullRequestExtractorService
from services.job_logging_service import JobLoggingService
from services.response_builder_service import FinalStatusResponse
from models import JobStatus, JobFields, JobActions

container = DependencyContainer()
pr_extractor = PullRequestExtractorService()
logging_service = JobLoggingService()

api_service_factory = ApiServiceFactory(pr_extractor, logging_service)

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
    executar_steps_incrementalmente: bool = Field(False, description="Se True, os passos do relatório de implementação serão executados de forma incremental (um ou mais passos por vez, respeitando dependências), ao invés de enviar todas as mudanças de uma só vez. Útil para relatórios extensos que podem exceder limites de tokens da LLM.")
    executar_build_dotnet: bool = Field(False, description="Se True, executa o build do projeto .NET após o commit e retorna os erros de compilação, se houver.")
    
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
def run_workflow_task(job_id: str, start_from_step: int = 0):
    workflow_orchestrator = container.get_workflow_orchestrator()
    workflow_orchestrator.execute_workflow(job_id, start_from_step)
@app.post("/start-analysis", response_model=StartAnalysisResponse, tags=["Jobs"])
def start_analysis(payload: StartAnalysisPayload, background_tasks: BackgroundTasks):
    job_store = container.get_job_store()
    analysis_service = container.get_analysis_name_service()
    repo_name = payload.repo_name_modernizado
    branch_name = payload.branch_name_modernizado
    print(f"[DEBUG][start_analysis] repo_name_modernizado recebido: {repo_name}")
    print(f"[DEBUG][start_analysis] branch_name_modernizado recebido: {branch_name}")
    normalized_repo_name = repository_normalizer_service.normalize_repo_name(
        repo_name, payload.repository_type
    )
    print(f"[DEBUG][start_analysis] normalized_repo_name: {normalized_repo_name}")
    print(f"[DEBUG][start_analysis] branch_name (não normalizado): {branch_name}")
    job_id = str(uuid.uuid4())
    analysis_name = job_data_service.generate_analysis_name(payload.analysis_name, job_id)
    payload_dict = payload.dict()
    payload_dict['analysis_type'] = payload.analysis_type.value
    payload_dict['repo_name_modernizado'] = normalized_repo_name
    payload_dict['branch_name_modernizado'] = branch_name
    print(f"[{job_id}] [DEBUG] Valor de executar_build_dotnet recebido no payload: {payload_dict.get('executar_build_dotnet')}")
    initial_job_data = job_data_service.create_initial_job_data(
        payload_dict, normalized_repo_name, analysis_name, branch_name
    )
    job_store.set_job(job_id, initial_job_data)
    logging_service.log_starting_job(job_id, payload_dict, normalized_repo_name, analysis_name)
    if analysis_name:
        analysis_service.register_analysis(analysis_name, job_id)
    print(f"[{job_id}] Job criado - Repositório: '{normalized_repo_name}' (tipo: {payload.repository_type}), Projeto: '{payload.projeto}'")
    background_tasks.add_task(run_workflow_task, job_id, start_from_step=0)
    return StartAnalysisResponse(job_id=job_id)
@app.post("/update-job-status", response_model=Dict[str, str], tags=["Jobs"])
def update_job_status(payload: UpdateJobPayload, background_tasks: BackgroundTasks):
    job_store = container.get_job_store()
    job = job_store.get_job(payload.job_id)
    job_validation_service.validate_job_for_approval(job, payload.job_id)
    if payload.action == JobActions.APPROVE:
        if payload.instrucoes_extras:
            job[JobFields.DATA][JobFields.INSTRUCOES_EXTRAS_APROVACAO] = payload.instrucoes_extras
            print(f"[{payload.job_id}] Instruções extras de aprovação salvas: {payload.instrucoes_extras[:100]}...")
        job[JobFields.STATUS] = JobStatus.WORKFLOW_STARTED
        paused_step = job[JobFields.DATA].get(JobFields.PAUSED_AT_STEP, 0)
        start_from_step = paused_step + 1
        job_store.set_job(payload.job_id, job)
        background_tasks.add_task(run_workflow_task, payload.job_id, start_from_step=start_from_step)
        return {"job_id": payload.job_id, JobFields.STATUS: JobStatus.WORKFLOW_STARTED, "message": "Aprovação recebida."}
    if payload.action == JobActions.REJECT:
        job[JobFields.STATUS] = JobStatus.REJECTED
        job_store.set_job(payload.job_id, job)
        return {"job_id": payload.job_id, JobFields.STATUS: JobStatus.REJECTED, "message": "Processo encerrado."}
@app.get("/jobs/{job_id}/report", response_model=ReportResponse, tags=["Jobs"])
def get_job_report(job_id: str = Path(..., title="O ID do Job para buscar o relatório")):
    job_store = container.get_job_store()
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    print(f"[{job_id}] [get_job_report] Buscando relatório. Job status: {job.get('status')}, gerar_relatorio_apenas: {job.get('data', {}).get('gerar_relatorio_apenas')}, analysis_report presente: {bool(job.get('data', {}).get('analysis_report'))}")
    job_validation_service.validate_job_exists(job, job_id)
    report = job_validation_service.get_report_from_job(job, job_id)
    blob_url = job.get(JobFields.DATA, {}).get(JobFields.REPORT_BLOB_URL)
    return ReportResponse(job_id=job_id, analysis_report=report, report_blob_url=blob_url)
@app.get("/analyses/by-name/{analysis_name}", response_model=AnalysisByNameResponse, tags=["Jobs"])
def get_analysis_by_name(analysis_name: str = Path(..., title="Nome da análise para buscar")):
    job_store = container.get_job_store()
    analysis_service = container.get_analysis_name_service()
    job_id = job_validation_service.validate_analysis_exists(analysis_name, analysis_service)
    job = job_store.get_job(job_id)
    job_validation_service.validate_job_exists(job, job_id)
    report = job.get(JobFields.DATA, {}).get(JobFields.ANALYSIS_REPORT)
    blob_url = job.get(JobFields.DATA, {}).get(JobFields.REPORT_BLOB_URL)
    return AnalysisByNameResponse(
        job_id=job_id,
        analysis_name=analysis_name,
        analysis_report=report,
        report_blob_url=blob_url
    )
@app.post("/start-code-generation-from-report/{analysis_name}", response_model=StartAnalysisResponse, tags=["Jobs"])
def start_code_generation_from_report(analysis_name: str, background_tasks: BackgroundTasks):
    job_store = container.get_job_store()
    analysis_service = container.get_analysis_name_service()
    job_id = job_validation_service.validate_analysis_exists(analysis_name, analysis_service)
    original_job = job_store.get_job(job_id)
    job_validation_service.validate_job_exists(original_job, job_id)
    report = job_validation_service.get_report_from_job(original_job, None)
    original_data = original_job[JobFields.DATA]
    original_repo_name = original_data[JobFields.REPO_NAME]
    original_branch_name = original_data.get(JobFields.BRANCH_NAME)
    original_repository_type = original_data[JobFields.REPOSITORY_TYPE]
    print(f"[DEBUG][start_code_generation_from_report] original_repo_name: {original_repo_name}")
    print(f"[DEBUG][start_code_generation_from_report] branch_name: {original_branch_name}")
    normalized_repo_name = repository_normalizer_service.normalize_repo_name(
        original_repo_name, original_repository_type
    )
    print(f"[DEBUG][start_code_generation_from_report] normalized_repo_name: {normalized_repo_name}")
    print(f"[DEBUG][start_code_generation_from_report] branch_name (não normalizado): {original_branch_name}")
    new_job_id = str(uuid.uuid4())
    new_job_data = job_data_service.create_derived_job_data(
        original_job, analysis_name, normalized_repo_name, report, original_branch_name
    )
    job_store.set_job(new_job_id, new_job_data)
    analysis_service.register_analysis(f"{analysis_name}-implementation", new_job_id)
    print(f"[{new_job_id}] Job derivado criado - Repositório: '{normalized_repo_name}' (tipo: {original_repository_type}), Projeto: '{original_data[JobFields.PROJETO]}'")
    background_tasks.add_task(run_workflow_task, new_job_id, start_from_step=0)
    return StartAnalysisResponse(job_id=new_job_id)

@app.get("/status/{job_id}", response_model=FinalStatusResponse, tags=["Jobs"])
def get_status(job_id: str = Path(..., title="O ID do Job a ser verificado")):
    job_store = container.get_job_store()
    job = job_store.get_job(job_id)
    job_validation_service.validate_job_exists(job, job_id)
    status = job.get(JobFields.STATUS) or "PROCESSING"
    job_data = job.get(JobFields.DATA, {})
    blob_url = job_data.get(JobFields.REPORT_BLOB_URL)
    gerar_relatorio_apenas = job_data.get(JobFields.GERAR_RELATORIO_APENAS, False)
    analysis_report = job_data.get(JobFields.ANALYSIS_REPORT, None)
    print(f"[{job_id}] [get_status] status: {status}")
    print(f"[{job_id}] [get_status] gerar_relatorio_apenas: {gerar_relatorio_apenas}")
    print(f"[{job_id}] [get_status] Tamanho analysis_report: {len(analysis_report) if analysis_report else 0}")
    print(f"[{job_id}] [get_status] report_blob_url: {blob_url}")
    try:
        if status == JobStatus.COMPLETED:
            return response_builder_service.build_completed_response(job_id, job, blob_url)
        elif status == JobStatus.FAILED:
            return response_builder_service.build_failed_response(job_id, job)
        else:
            return FinalStatusResponse(job_id=job_id, status=status, report_blob_url=blob_url, build_errors=job_data.get('build_errors'))
    except ValidationError as e:
        print(f"ERRO CRÍTICO de Validação no Job ID {job_id}: {e}")
        print(f"Dados brutos do job que causaram o erro: {job}")
        raise
@app.get("/reports/{report_name}/jobs", response_model=List[str], tags=["Reports"])
def get_jobs_for_report(report_name: str):
    blob_storage = container.get_blob_storage()
    container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME')
    account_url = os.getenv('AZURE_STORAGE_ACCOUNT_URL')
    if not container_name or not account_url:
        raise HTTPException(status_code=500, detail="Configuração de Blob Storage ausente.")
    report_blob_url = f"{account_url}/{container_name}/{report_name}"
    try:
        jobs = blob_storage.get_jobs_for_report(report_blob_url)
        return jobs
    except Exception as e:
        print(f"[API] Warning: Failed to get jobs for report {report_blob_url}: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar jobs associados ao relatório.")
