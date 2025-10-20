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
from models import JobStatus, JobFields, JobActions, EpicoResponse, TarefaResponse, TarefaCard
from services.epico_parser_service import EpicoParserService
from services.tarefa_parser_service import TarefaParserService

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
    transcricao_reuniao: Optional[str] = None
    gerar_epicos: bool = False
    criar_cards_azure: bool = False
    azure_project_name: Optional[str] = None
    gerar_tarefas: bool = False
    epicos_aprovados: Optional[List[str]] = None

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
    print(f"[{job_id}] [DEBUG] Valor de executar_build_dotnet recebido no payload: {payload_dict.get('executar_build_dotnet')}")
    payload_dict['branch_name_modernizado'] = branch_name
    # Inclui os campos do novo fluxo
    payload_dict['gerar_tarefas'] = payload_dict.get('gerar_tarefas', False)
    payload_dict['epicos_aprovados'] = payload_dict.get('epicos_aprovados')
    initial_job_data = job_data_service.create_initial_job_data(
        payload_dict, normalized_repo_name, analysis_name
    )
    print(f"[{job_id}] [DEBUG] Valor de branch_name_modernizado passado para create_initial_job_data: {branch_name}")
    job_store.set_job(job_id, initial_job_data)
    logging_service.log_starting_job(job_id, payload_dict, normalized_repo_name, analysis_name)
    if analysis_name:
        analysis_service.register_analysis(analysis_name, job_id)
    print(f"[{job_id}] Job criado - Repositório: '{normalized_repo_name}' (tipo: {payload.repository_type}), Projeto: '{payload.projeto}'")
    background_tasks.add_task(run_workflow_task, job_id, start_from_step=0)
    return StartAnalysisResponse(job_id=job_id)
# ... outros endpoints permanecem inalterados ...
@app.get("/jobs/{job_id}/tarefas", response_model=TarefaResponse, tags=["Tarefas"])
def get_tarefas(job_id: str = Path(..., title="O ID do Job para buscar as tarefas")):
    job_store = container.get_job_store()
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job_data = job.get(JobFields.DATA, {})
    if not job_data.get('gerar_tarefas', False):
        raise HTTPException(status_code=400, detail="Este job não é do tipo geração de tarefas.")
    analysis_report = job_data.get('analysis_report')
    if not analysis_report:
        raise HTTPException(status_code=404, detail="Relatório de tarefas não encontrado para este job.")
    observacoes_aprovacao = job_data.get('instrucoes_extras_aprovacao')
    epicos_aprovados = []
    if observacoes_aprovacao:
        for line in observacoes_aprovacao.splitlines():
            line = line.strip()
            if line.startswith('E') and len(line) >= 3:
                epicos_aprovados.append(line.split()[0])
            elif ',' in line:
                epicos_aprovados.extend([e.strip() for e in line.split(',') if e.strip().startswith('E')])
    if not epicos_aprovados:
        raise HTTPException(status_code=400, detail="Não foi possível identificar os épicos aprovados a partir das observações de aprovação.")
    tarefas = []
    for epico_id in epicos_aprovados:
        tarefas.extend(TarefaParserService.parse_tarefas_from_report(analysis_report, epico_id))
    tarefas_criadas = job_data.get('tarefas_criadas', None)
    return TarefaResponse(job_id=job_id, tarefas=tarefas, tarefas_criadas=tarefas_criadas)
