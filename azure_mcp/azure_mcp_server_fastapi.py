import os
import uuid
from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from azure_mcp.services.azure_job_validation_service import AzureJobValidationService
from services.job_handler import JobHandler
from services.response_builder_service import FinalStatusResponse, ResponseBuilderService
from services.report_handler import ReportHandler
from services.job_store import JobStore
from services.blob_storage_service import BlobStorageService
from azure_mcp.services.azure_dependency_container import AzureDependencyContainer
from azure_mcp.services.azure_workflow_orchestrator import AzureWorkflowOrchestrator

# --- Payloads ---
class StartAzureAnalysisPayload(BaseModel):
    analysis_type: Literal['criacao_epicos_azure_devops', 'criacao_tarefas_azure_devops', 'revisor_tarefas', 'criacao_features_azure_devops']
    repo_name_modernizado: Optional[str] = Field(None, description="Nome do repositório modernizado")
    branch_name_modernizado: Optional[str] = Field(None, description="Branch do repositório modernizado")
    projeto: Optional[str] = Field(None, description="Nome do projeto para agrupar atividades e organizar histórico")
    instrucoes_extras: Optional[str] = None
    model_name: Optional[str] = Field(None, description="Nome do modelo de LLM a ser usado. Se nulo, usa o padrão.")
    arquivos_especificos: Optional[List[str]] = Field(None, description="Lista opcional de caminhos específicos de arquivos para ler.")
    analysis_name: Optional[str] = Field(None, description="Nome personalizado para identificar a análise.")
    repository_type: Literal['github', 'gitlab', 'azure'] = Field(description="Tipo do repositório.")
    epic_id: Optional[str] = Field(None, description="ID do épico do Azure DevOps para geração de tarefas.")
    feature_id: Optional[str] = Field(None, description="ID da feature do Azure DevOps.")
    task_id: Optional[str] = Field(None, description="ID da tarefa do Azure DevOps.")
    organization: Optional[str] = Field(None, description="Organização do Azure DevOps.")
    project: Optional[str] = Field(None, description="Projeto do Azure DevOps.")

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

app = FastAPI(
    title="MCP Azure Server",
    description="Servidor dedicado para análise e automação Azure DevOps.",
    version="1.0.0"
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

container = AzureDependencyContainer()
workflow_orchestrator = AzureWorkflowOrchestrator(container)
job_handler = JobHandler(container.get_job_manager())
job_store = container.get_job_store()
report_handler = ReportHandler(container.get_blob_storage())
response_builder_service = ResponseBuilderService()
job_validation_service = AzureJobValidationService()

@app.post("/start-azure-analysis", response_model=StartAnalysisResponse, tags=["Jobs"])
def start_azure_analysis(payload: StartAzureAnalysisPayload, background_tasks: BackgroundTasks):
    # Validação específica Azure
    job_validation_service.validate_payload(payload)
    job_id = str(uuid.uuid4())
    initial_job_data = job_handler.create_initial_job_data(payload.dict(), payload.repo_name_modernizado, payload.analysis_name)
    job_store.set_job(job_id, initial_job_data)
    background_tasks.add_task(workflow_orchestrator.execute_workflow, job_id, start_from_step=0)
    return StartAnalysisResponse(job_id=job_id)

@app.post("/update-job-status", response_model=Dict[str, str], tags=["Jobs"])
def update_job_status(payload: UpdateJobPayload, background_tasks: BackgroundTasks):
    job = job_store.get_job(payload.job_id)
    job_validation_service.validate_job_for_approval(job, payload.job_id)
    current_status = job.get('status')
    if payload.action == "approve":
        if current_status != "pending_approval":
            raise HTTPException(status_code=400, detail="Ação de aprovação só é permitida quando o job está em pending_approval.")
        if payload.instrucoes_extras:
            job['data']['instrucoes_extras_aprovacao'] = payload.instrucoes_extras
        job['status'] = "workflow_started"
        paused_step = job['data'].get('paused_at_step', 0)
        start_from_step = paused_step + 1
        job_store.set_job(payload.job_id, job)
        background_tasks.add_task(workflow_orchestrator.execute_workflow, payload.job_id, start_from_step=start_from_step)
        return {"job_id": payload.job_id, "status": "workflow_started", "message": "Aprovação recebida."}
    if payload.action == "reject":
        if current_status != "pending_approval":
            raise HTTPException(status_code=400, detail="Ação de rejeição só é permitida quando o job está em pending_approval.")
        job['status'] = "rejected"
        job_store.set_job(payload.job_id, job)
        return {"job_id": payload.job_id, "status": "rejected", "message": "Processo encerrado."}

@app.get("/status/{job_id}", response_model=FinalStatusResponse, tags=["Jobs"])
def get_status(job_id: str = Path(..., title="O ID do Job a ser verificado")):
    job = job_store.get_job(job_id)
    job_validation_service.validate_job_exists(job, job_id)
    status = job.get('status') or "PROCESSING"
    job_data = job.get('data', {})
    blob_url = job_data.get('report_blob_url')
    analysis_report = job_data.get('analysis_report', None)
    build_errors = job_data.get('build_errors')
    return FinalStatusResponse(job_id=job_id, status=status, report_blob_url=blob_url, analysis_report=analysis_report, build_errors=build_errors)

@app.get("/jobs/{job_id}/report", response_model=ReportResponse, tags=["Jobs"])
def get_job_report(job_id: str = Path(..., title="O ID do Job para buscar o relatório")):
    job = job_store.get_job(job_id)
    job_validation_service.validate_job_exists(job, job_id)
    report = job.get('data', {}).get('analysis_report')
    blob_url = job.get('data', {}).get('report_blob_url')
    return ReportResponse(job_id=job_id, analysis_report=report, report_blob_url=blob_url)
