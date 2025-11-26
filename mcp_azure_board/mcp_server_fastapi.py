import json
import uuid
import time
import traceback
import os
from typing import Optional, List, Dict, Any, Literal
from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel, Field, ValidationError
from fastapi.middleware.cors import CORSMiddleware
from services.dependency_container import DependencyContainer
from services.workflow_registry_service import WorkflowRegistryService
from services.api_service_factory import ApiServiceFactory
from services.job_logging_service import JobLoggingService
from models import JobStatus, JobFields, JobActions, ValidAnalysisTypes, FinalStatusResponse

container = DependencyContainer()
logging_service = JobLoggingService()
api_service_factory = ApiServiceFactory(logging_service=logging_service)
workflow_registry_service = container.get_workflow_registry_service()
ValidAnalysisTypes = workflow_registry_service.get_valid_analysis_types()
response_builder_service = api_service_factory.get_response_builder_service()
repository_normalizer_service = api_service_factory.get_repository_normalizer_service()
job_data_service = api_service_factory.get_job_data_service()
job_validation_service = api_service_factory.get_job_validation_service()
logging_service = api_service_factory.get_logging_service()

class StartAnalysisPayload(BaseModel):
    projeto: Optional[str] = Field(None, description="Nome do projeto para agrupar atividades e organizar histórico")
    analysis_type: ValidAnalysisTypes
    instrucoes_extras: Optional[str] = None
    usar_rag: bool = Field(False)
    gerar_relatorio_apenas: bool = Field(False)
    model_name: Optional[str] = Field(None, description="Nome do modelo de LLM a ser usado. Se nulo, usa o padrão.")
    arquivos_especificos: Optional[List[str]] = Field(None, description="Lista opcional de caminhos específicos de arquivos para ler. Se fornecido, apenas esses arquivos serão processados.")
    analysis_name: Optional[str] = Field(None, description="Nome personalizado para identificar a análise.")
    repository_type: Literal['azure'] = Field(description="Tipo do repositório: apenas 'azure' para este MCP.")
    retornar_lista_arquivos: bool = False
    usuario_executor: Optional[str] = None
    executar_steps_incrementalmente: bool = Field(True, description="[DEPRECATED: O valor False está descontinuado e será removido em versões futuras. Use sempre True.] Se True, os passos do relatório de implementação serão executados de forma incremental.")
    max_steps_per_batch: Optional[int] = Field(3, description="Número máximo de steps por batch na execução incremental")

class StartAnalysisResponse(BaseModel):
    job_id: str

class UpdateJobPayload(BaseModel):
    job_id: str
    action: Literal["approve", "reject"]
    instrucoes_extras: Optional[str] = None

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
    title="MCP Azure Board Server",
    description="Servidor dedicado para operações Azure Boards.",
    version="1.0.0"
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def run_workflow_task(job_id: str, start_from_step: int = 0):
    workflow_orchestrator = container.get_workflow_orchestrator()
    workflow_orchestrator.execute_workflow(job_id, start_from_step)

@app.post("/start-analysis", response_model=StartAnalysisResponse, tags=["Jobs"])
def start_analysis(payload: StartAnalysisPayload, background_tasks: BackgroundTasks):
    workflows = workflow_registry_service.get_workflow_registry()
    workflow = workflows.get(payload.analysis_type)
    job_store = container.get_job_store()
    analysis_service = container.get_analysis_name_service()
    job_id = str(uuid.uuid4())
    analysis_name = job_data_service.generate_analysis_name(payload.analysis_name, job_id)
    payload_dict = payload.dict()
    if hasattr(payload.analysis_type, 'value'):
        payload_dict['analysis_type'] = payload.analysis_type.value
    initial_job_data = job_data_service.create_initial_job_data(
        payload_dict, None, analysis_name
    )
    job_store.set_job(job_id, initial_job_data)
    logging_service.log_starting_job(job_id, payload_dict, None, analysis_name)
    if analysis_name:
        analysis_service.register_analysis(analysis_name, job_id)
    background_tasks.add_task(run_workflow_task, job_id, start_from_step=0)
    return StartAnalysisResponse(job_id=job_id)

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
    try:
        if status == JobStatus.COMPLETED:
            return response_builder_service.build_completed_response(job_id, job, blob_url)
        elif status == JobStatus.FAILED:
            return response_builder_service.build_failed_response(job_id, job)
        else:
            return FinalStatusResponse(job_id=job_id, status=status, report_blob_url=blob_url)
    except ValidationError as e:
        raise

@app.get("/jobs/{job_id}/report", response_model=ReportResponse, tags=["Jobs"])
def get_job_report(job_id: str = Path(..., title="O ID do Job para buscar o relatório")):
    job_store = container.get_job_store()
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
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
