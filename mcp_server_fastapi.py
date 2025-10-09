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
    checkpoint_available: Optional[bool] = Field(False, description="Indica se há checkpoint disponível para retomada da execução incremental.")
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
    payload_dict['job_id'] = job_id
    initial_job_data = job_data_service.create_initial_job_data(
        payload_dict, normalized_repo_name, analysis_name
    )
    job_store.set_job(job_id, initial_job_data)
    saved_job = job_store.get_job(job_id)
    aplicar_incremental_salvo = saved_job.get('data', {}).get('aplicar_mudancas_incrementalmente', False)
    print(f"[{job_id}] Validação pós-criação - aplicar_mudancas_incrementalmente: {aplicar_incremental_salvo}")
    if payload.aplicar_mudancas_incrementalmente and not aplicar_incremental_salvo:
        print(f"[{job_id}] WARNING CRÍTICO: Flag aplicar_mudancas_incrementalmente deveria ser True mas está False após persistência!")
    logging_service.log_starting_job(job_id, payload_dict, normalized_repo_name, analysis_name)
    if analysis_name:
        analysis_service.register_analysis(analysis_name, job_id)
    print(f"[{job_id}] Job criado - Repositório: '{normalized_repo_name}' (tipo: {payload.repository_type}), Projeto: '{payload.projeto}'")
    background_tasks.add_task(run_workflow_task, job_id, start_from_step=0)
    checkpoint_available = False
    context_cache_service = container.get_context_cache_service()
    checkpoint_key = f"checkpoint:{job_id}"
    try:
        checkpoint = context_cache_service.get_checkpoint(checkpoint_key)
        if checkpoint:
            checkpoint_available = True
    except Exception:
        checkpoint_available = False
    return StartAnalysisResponse(job_id=job_id, checkpoint_available=checkpoint_available)
@app.get("/status/{job_id}", response_model=FinalStatusResponse, tags=["Jobs"])
def get_status(job_id: str = Path(..., title="O ID do Job a ser verificado")):
    job_store = container.get_job_store()
    job = job_store.get_job(job_id)
    job_validation_service.validate_job_exists(job, job_id)
    status = job.get(JobFields.STATUS)
    job_data = job.get(JobFields.DATA, {})
    blob_url = job_data.get(JobFields.REPORT_BLOB_URL)
    gerar_relatorio_apenas = job_data.get(JobFields.GERAR_RELATORIO_APENAS, False)
    analysis_report = job_data.get(JobFields.ANALYSIS_REPORT, None)
    incremental_execution_summary = job_data.get('incremental_execution_summary')
    aplicar_incremental = job_data.get('aplicar_mudancas_incrementalmente', False)
    print(f"[{job_id}] [get_status] status: {status}")
    print(f"[{job_id}] [get_status] gerar_relatorio_apenas: {gerar_relatorio_apenas}")
    print(f"[{job_id}] [get_status] aplicar_mudancas_incrementalmente: {aplicar_incremental}")
    print(f"[{job_id}] [get_status] Tamanho analysis_report: {len(analysis_report) if analysis_report else 0}")
    print(f"[{job_id}] [get_status] report_blob_url: {blob_url}")
    print(f"[{job_id}] [get_status] commit_details: {job_data.get('commit_details')}")
    print(f"[{job_id}] [get_status] incremental_execution_summary: {incremental_execution_summary}")
    print(f"[{job_id}] [get_status] DEBUG - job_data completo: {json.dumps(job_data, indent=2)}")
    if incremental_execution_summary:
        print(f"[{job_id}] [API] Retornando incremental_execution_summary: {incremental_execution_summary}")
        print(f"[{job_id}] [API] commit_details: {job_data.get('commit_details')}")
    try:
        if status == JobStatus.COMPLETED:
            response = response_builder_service.build_completed_response(job_id, job, blob_url)
            print(f"[{job_id}] [get_status] Conteúdo do campo summary da resposta: {getattr(response, 'summary', None)}")
            if not getattr(response, 'summary', None):
                print(f"[{job_id}] [get_status] ERROR: Campo summary vazio ou None para job COMPLETED.")
            return response
        elif status == JobStatus.FAILED:
            return response_builder_service.build_failed_response(job_id, job)
        else:
            return FinalStatusResponse(job_id=job_id, status=status, report_blob_url=blob_url, incremental_execution_summary=incremental_execution_summary)
    except ValidationError as e:
        print(f"ERRO CRÍTICO de Validação no Job ID {job_id}: {e}")
        print(f"Dados brutos do job que causaram o erro: {job}")
        raise
