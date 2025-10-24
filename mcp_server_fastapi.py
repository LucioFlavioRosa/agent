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
    model_name: Optional[str] = Field(None, description="Nome do modelo de LLM a ser usado. Se nulo, usa o padrão.")
    arquivos_especificos: Optional[List[str]] = Field(None, description="Lista opcional de caminhos específicos de arquivos para ler. Se fornecido, apenas esses arquivos serão processados.")
    analysis_name: Optional[str] = Field(None, description="Nome personalizado para identificar a análise.")
    repository_type: Literal['github', 'gitlab', 'azure'] = Field(description="Tipo do repositório: 'github', 'gitlab', 'azure'.")
    repo_name_original: Optional[str] = Field(None, description="Nome do repositório original para comparação")
    branch_name_original: Optional[str] = Field(None, description="Branch do repositório original")
    retornar_lista_arquivos: bool = False
    usuario_executor: Optional[str] = None
    executar_steps_incrementalmente: bool = Field(
        True, description="[DEPRECATED: O valor False está descontinuado e será removido em versões futuras. Use sempre True.] Se True, os passos do relatório de implementação serão executados de forma incremental (um ou mais passos por vez, respeitando dependências), ao invés de enviar todas as mudanças de uma só vez. Útil para relatórios extensos que podem exceder limites de tokens da LLM.")
    max_steps_per_batch: Optional[int] = Field(3, description="Número máximo de steps por batch na execução incremental")
    executar_build_dotnet: bool = Field(False, description="Se True, executa o build do projeto .NET após o commit e retorna os erros de compilação, se houver.")
    criar_epicos_azure: bool = Field(False, description="Se True, após aprovação, cria os épicos no Azure DevOps Board")
    criar_tarefas_azure: bool = Field(False, description="Se True, após aprovação do relatório de tarefas, cria os Work Items no Azure DevOps Board dentro do épico especificado.")
    epic_id: Optional[str] = Field(None, description="ID do épico do Azure DevOps para geração de tarefas. Obrigatório quando analysis_type for 'criacao_tarefas_azure_devops'.")
    
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
    print(f"[DEBUG] /start-analysis payload.criar_tarefas_azure={getattr(payload, 'criar_tarefas_azure', None)}")
    if getattr(payload, 'criar_epicos_azure', False):
        if not payload.instrucoes_extras or not str(payload.instrucoes_extras).strip():
            raise HTTPException(status_code=400, detail="instrucoes_extras (transcrição da reunião) é obrigatório para criar épicos.")
        print(f"[DEBUG] Fluxo de criação de épicos acionado para repo: {payload.repo_name_modernizado}")
    if getattr(payload, 'criar_tarefas_azure', False):
        if not getattr(payload, 'epic_id', None):
            raise HTTPException(status_code=400, detail="epic_id é obrigatório quando criar_tarefas_azure=True.")
        print(f"[DEBUG] Fluxo de criação de tarefas Azure acionado para repo: {payload.repo_name_modernizado}, epic_id={getattr(payload, 'epic_id', None)}")
    else:
        if payload.executar_steps_incrementalmente is False and payload.gerar_relatorio_apenas is False:
            raise HTTPException(status_code=400, detail="Modo não-incremental descontinuado. Use executar_steps_incrementalmente=True ou gerar_relatorio_apenas=True.")
    analysis_type_str = str(payload.analysis_type.value) if hasattr(payload.analysis_type, 'value') else str(payload.analysis_type)
    if analysis_type_str == 'criacao_tarefas_azure_devops':
        if not getattr(payload, 'epic_id', None):
            raise HTTPException(status_code=400, detail="epic_id é obrigatório para análise do tipo criacao_tarefas_azure_devops.")
    workflows = workflow_registry_service.get_workflow_registry()
    workflow = workflows.get(payload.analysis_type)
    first_step = None
    requires_approval_value = None
    if workflow and 'steps' in workflow and len(workflow['steps']) > 0:
        first_step = workflow['steps'][0]
        requires_approval_value = first_step.get('requires_approval')
        print(f"[DEBUG] Valor de requires_approval do primeiro step: {requires_approval_value}")
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
    if hasattr(payload.analysis_type, 'value'):
        payload_dict['analysis_type'] = payload.analysis_type.value
    if analysis_type_str == 'criacao_tarefas_azure_devops':
        repo_parts = repo_name.split('/')
        if len(repo_parts) < 2:
            raise HTTPException(status_code=400, detail="repo_name_modernizado deve conter organização e projeto separados por '/'.")
        payload_dict['organization'] = repo_parts[0]
        payload_dict['project'] = repo_parts[1]
    initial_job_data = job_data_service.create_initial_job_data(
        payload_dict, normalized_repo_name, analysis_name
    )
    print(f"[DEBUG] initial_job_data['data']['criar_tarefas_azure']={initial_job_data['data'].get('criar_tarefas_azure')}")
    job_store.set_job(job_id, initial_job_data)
    logging_service.log_starting_job(job_id, payload_dict, normalized_repo_name, analysis_name)
    if analysis_name:
        analysis_service.register_analysis(analysis_name, job_id)
    background_tasks.add_task(run_workflow_task, job_id, start_from_step=0)
    return StartAnalysisResponse(job_id=job_id)
# ...restante do arquivo permanece igual...
