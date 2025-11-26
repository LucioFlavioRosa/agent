import uuid
import os
from typing import Optional, Dict, Any
from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel, Field, ValidationError
from fastapi.middleware.cors import CORSMiddleware
from mcp_azure_board.models import EpicCreationPayload, JobStatus, JobFields, JobActions, ValidAnalysisTypes
from services.dependency_container import DependencyContainer
from services.workflow_registry_service import WorkflowRegistryService
from services.api_service_factory import ApiServiceFactory
from services.job_logging_service import JobLoggingService
from services.response_builder_service import FinalStatusResponse

container = DependencyContainer()
logging_service = JobLoggingService()
api_service_factory = ApiServiceFactory(logging_service=logging_service)
workflow_registry_service = container.get_workflow_registry_service()
ValidAnalysisTypesAzure = [t.value for t in ValidAnalysisTypes]
response_builder_service = api_service_factory.get_response_builder_service()
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
    analysis_name: Optional[str] = Field(None, description="Nome personalizado para identificar a análise.")
    repository_type: str = Field(description="Tipo do repositório: 'azure'.")
    retornar_lista_arquivos: bool = False
    usuario_executor: Optional[str] = None
    executar_steps_incrementalmente: bool = Field(True, description="Sempre True para Azure Board MCP.")
    max_steps_per_batch: Optional[int] = Field(3, description="Número máximo de steps por batch na execução incremental")
    executar_build_dotnet: bool = Field(False, description="Se True, executa o build do projeto .NET após o commit e retorna os erros de compilação, se houver.")
    epic_id: Optional[str] = Field(None, description="ID do épico do Azure DevOps para geração de tarefas. Obrigatório quando analysis_type para 'criacao_features_azure_devops'.")
    feature_id: Optional[str] = Field(None, description="ID da feature do Azure DevOps. Obrigatório apenas quando analysis_type for 'criacao_tarefas_azure_devops'.")
    task_id: Optional[str] = Field(None, description="ID da tarefa do Azure DevOps. Obrigatório apenas quando analysis_type for 'revisor_tarefas'.")

class StartAnalysisResponse(BaseModel):
    job_id: str

class UpdateJobPayload(BaseModel):
    job_id: str
    action: str
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
    title="MCP Azure Board",
    description="Servidor FastAPI dedicado às operações do Azure Board (épicos, features, tarefas, revisões)",
    version="1.0.0"
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def run_workflow_task(job_id: str, start_from_step: int = 0):
    workflow_orchestrator = container.get_workflow_orchestrator()
    workflow_orchestrator.execute_workflow(job_id, start_from_step)

@app.post("/start-analysis", response_model=StartAnalysisResponse, tags=["Jobs"])
def start_analysis(payload: StartAnalysisPayload, background_tasks: BackgroundTasks):
    analysis_type_str = str(payload.analysis_type.value) if hasattr(payload.analysis_type, 'value') else str(payload.analysis_type)
    if analysis_type_str not in ValidAnalysisTypesAzure:
        raise HTTPException(status_code=400, detail=f"analysis_type '{analysis_type_str}' não suportado neste MCP.")
    if analysis_type_str == 'criacao_features_azure_devops':
        if not getattr(payload, 'epic_id', None) or (isinstance(payload.epic_id, str) and not payload.epic_id.strip()):
            raise HTTPException(status_code=400, detail="epic_id é obrigatório para análise do tipo criacao_features_azure_devops.")
    if analysis_type_str == 'criacao_tarefas_azure_devops':
        if not getattr(payload, 'feature_id', None) or (isinstance(payload.feature_id, str) and not payload.feature_id.strip()):
            raise HTTPException(status_code=400, detail="feature_id é obrigatório para análise do tipo criacao_tarefas_azure_devops.")
    if analysis_type_str == 'revisor_tarefas':
        if not getattr(payload, 'task_id', None) or (isinstance(payload.task_id, str) and not payload.task_id.strip()):
            raise HTTPException(status_code=400, detail="task_id é obrigatório para análise do tipo revisor_tarefas.")
    if payload.executar_steps_incrementalmente is False and payload.gerar_relatorio_apenas is False:
        raise HTTPException(status_code=400, detail="Modo não-incremental descontinuado. Use executar_steps_incrementalmente=True ou gerar_relatorio_apenas=True.")
    workflows = workflow_registry_service.get_workflow_registry()
    workflow = workflows.get(payload.analysis_type)
    first_step = None
    requires_approval_value = None
    if workflow and 'steps' in workflow and len(workflow['steps']) > 0:
        first_step = workflow['steps'][0]
        requires_approval_value = first_step.get('requires_approval')
    job_store = container.get_job_store()
    analysis_service = container.get_analysis_name_service()
    job_id = str(uuid.uuid4())
    analysis_name = job_data_service.generate_analysis_name(payload.analysis_name, job_id)
    payload_dict = payload.dict()
    if hasattr(payload.analysis_type, 'value'):
        payload_dict['analysis_type'] = payload.analysis_type.value
    # Propagação de organization/project para Azure Board
    if analysis_type_str in ['criacao_tarefas_azure_devops', 'revisor_tarefas', 'criacao_features_azure_devops', 'criacao_epicos_azure_devops']:
        # Espera-se que o nome do projeto seja passado corretamente
        pass
    initial_job_data = job_data_service.create_initial_job_data(
        payload_dict, None, analysis_name
    )
    job_store.set_job(job_id, initial_job_data)
    logging_service.log_starting_job(job_id, payload_dict, None, analysis_name)
    if analysis_name:
        analysis_service.register_analysis(analysis_name, job_id)
    background_tasks.add_task(run_workflow_task, job_id, start_from_step=0)
    return StartAnalysisResponse(job_id=job_id)

@app.post("/update-job-status", response_model=Dict[str, str], tags=["Jobs"])
def update_job_status(payload: UpdateJobPayload, background_tasks: BackgroundTasks):
    job_store = container.get_job_store()
    job = job_store.get_job(payload.job_id)
    job_validation_service.validate_job_for_approval(job, payload.job_id)
    if job.get('data', {}).get('executar_steps_incrementalmente') is False and job.get('data', {}).get('gerar_relatorio_apenas') is False:
        raise HTTPException(status_code=400, detail="Não é possível aprovar jobs no modo não-incremental (descontinuado).")
    current_status = job.get(JobFields.STATUS)
    if payload.action == JobActions.APPROVE:
        if current_status != JobStatus.PENDING_APPROVAL:
            raise HTTPException(status_code=400, detail="Ação de aprovação só é permitida quando o job está em pending_approval.")
        if payload.instrucoes_extras:
            job[JobFields.DATA][JobFields.INSTRUCOES_EXTRAS_APROVACAO] = payload.instrucoes_extras
        job[JobFields.STATUS] = JobStatus.WORKFLOW_STARTED
        paused_step = job[JobFields.DATA].get(JobFields.PAUSED_AT_STEP, 0)
        start_from_step = paused_step + 1
        job_store.set_job(payload.job_id, job)
        background_tasks.add_task(run_workflow_task, payload.job_id, start_from_step=start_from_step)
        return {"job_id": payload.job_id, JobFields.STATUS: JobStatus.WORKFLOW_STARTED, "message": "Aprovação recebida."}
    if payload.action == JobActions.REJECT:
        if current_status != JobStatus.PENDING_APPROVAL:
            raise HTTPException(status_code=400, detail="Ação de rejeição só é permitida quando o job está em pending_approval.")
        job[JobFields.STATUS] = JobStatus.REJECTED
        job_store.set_job(payload.job_id, job)
        return {"job_id": payload.job_id, JobFields.STATUS: JobStatus.REJECTED, "message": "Processo encerrado."}

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
            return FinalStatusResponse(job_id=job_id, status=status, report_blob_url=blob_url, build_errors=job_data.get('build_errors'))
    except ValidationError as e:
        raise
