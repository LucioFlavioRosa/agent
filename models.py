from pydantic import BaseModel, Field, validator, model_validator, ValidationError
from typing import List, Dict, Any, Optional, Literal
from enum import Enum

class EpicCreationPayload(BaseModel):
    transcricao_reuniao: str = Field(..., description="Transcrição da reunião para geração de épicos")
    criar_epicos_azure: bool = Field(False, description="Se True, após aprovação, cria os épicos no Azure DevOps Board")

class PullRequestSummary(BaseModel):
    pull_request_url: str
    branch_name: str
    arquivos_modificados: List[str]
    build_result: Optional[Dict[str, Any]] = None
    commit_url: Optional[str] = None

class FinalStatusResponse(BaseModel):
    job_id: str
    status: str
    summary: Optional[List[PullRequestSummary]] = None
    error_details: Optional[str] = None
    analysis_report: Optional[str] = None
    diagnostic_logs: Optional[Dict[str, Any]] = None
    report_blob_url: Optional[str] = None
    build_errors: Optional[List[str]] = None

class JobStatus:
    STARTING = 'starting'
    PENDING_APPROVAL = 'pending_approval'
    WORKFLOW_STARTED = 'workflow_started'
    COMPLETED = 'completed'
    FAILED = 'failed'
    REJECTED = 'rejected'

class JobFields:
    STATUS = 'status'
    DATA = 'data'
    ERROR_DETAILS = 'error_details'
    REPO_NAME = 'repo_name'
    ORIGINAL_REPO_NAME = 'original_repo_name'
    PROJETO = 'projeto'
    BRANCH_NAME = 'branch_name'
    ORIGINAL_ANALYSIS_TYPE = 'original_analysis_type'
    INSTRUCOES_EXTRAS = 'instrucoes_extras'
    MODEL_NAME = 'model_name'
    USAR_RAG = 'usar_rag'
    GERAR_RELATORIO_APENAS = 'gerar_relatorio_apenas'
    ARQUIVOS_ESPECIFICOS = 'arquivos_especificos'
    ANALYSIS_NAME = 'analysis_name'
    REPOSITORY_TYPE = 'repository_type'
    ANALYSIS_REPORT = 'analysis_report'
    REPORT_BLOB_URL = 'report_blob_url'
    COMMIT_DETAILS = 'commit_details'
    DIAGNOSTIC_LOGS = 'diagnostic_logs'
    INSTRUCOES_EXTRAS_APROVACAO = 'instrucoes_extras_aprovacao'
    PAUSED_AT_STEP = 'paused_at_step'
    SUCCESS = 'success'
    PR_URL = 'pr_url'
    ARQUIVOS_MODIFICADOS = 'arquivos_modificados'
    REPO_NAME_MODERNIZADO = 'repo_name_modernizado'
    BRANCH_NAME_MODERNIZADO = 'branch_name_modernizado'
    REPO_NAME_ORIGINAL = 'repo_name_original'
    BRANCH_NAME_ORIGINAL = 'branch_name_original'
    RETORNAR_LISTA_ARQUIVOS = 'retornar_lista_arquivos'
    USUARIO_EXECUTOR = 'usuario_executor'
    EXECUTAR_STEPS_INCREMENTALMENTE = 'executar_steps_incrementalmente'
    STEP_BATCHES = 'step_batches'
    CURRENT_BATCH_INDEX = 'current_batch_index'
    BATCH_RESULTS = 'batch_results'
    MAX_STEPS_PER_BATCH = 'max_steps_per_batch'
    EXECUTAR_BUILD_DOTNET = 'executar_build_dotnet'
    BUILD_ERRORS = 'build_errors'
    BUILD_RESULT = 'build_result'
    REQUIRES_APPROVAL = 'requires_approval'
    AZURE_ORGANIZATION = 'azure_organization'
    AZURE_PROJECT = 'azure_project'
    EPICOS_CRIADOS = 'epicos_criados'
    EPIC_ID = 'epic_id'
    ORGANIZATION = 'organization'
    PROJECT = 'project'
    TASK_ID = 'task_id'
    FEATURE_ID = 'feature_id'

class JobActions:
    APPROVE = 'approve'
    REJECT = 'reject'

class ValidAnalysisTypes(str, Enum):
    MODERNIZACAO = 'modernizacao'
    IMPLEMENTACAO = 'implementacao'
    CRIACAO_EPICOS = 'criacao_epicos'
    REVISOR_TAREFAS = 'revisor_tarefas'
