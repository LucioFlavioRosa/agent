from pydantic import BaseModel, Field, validator, root_validator
from typing import List, Dict, Any, Optional

class PullRequestSummary(BaseModel):
    pull_request_url: str
    branch_name: str
    arquivos_modificados: List[str]
    build_result: Optional[Dict[str, Any]] = None
    commit_url: Optional[str] = None
    build_errors: Optional[List[str]] = None

class EpicSummary(BaseModel):
    epic_id: str
    epic_url: Optional[str] = None
    epic_title: Optional[str] = None

class FinalStatusResponse(BaseModel):
    job_id: str
    status: str
    summary: Optional[List[PullRequestSummary]] = None
    error_details: Optional[str] = None
    analysis_report: Optional[str] = None
    diagnostic_logs: Optional[Dict[str, Any]] = None
    report_blob_url: Optional[str] = None
    build_errors: Optional[List[str]] = None
    epics_created: Optional[List[EpicSummary]] = None

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
    GERAR_NOVO_RELATORIO = 'gerar_novo_relatorio'
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
    MODO_ADICAO_INCREMENTAL = 'modo_adicao_incremental'
    USUARIO_EXECUTOR = 'usuario_executor'
    EXECUTAR_STEPS_INCREMENTALMENTE = 'executar_steps_incrementalmente'
    STEP_BATCHES = 'step_batches'
    CURRENT_BATCH_INDEX = 'current_batch_index'
    BATCH_RESULTS = 'batch_results'
    MAX_STEPS_PER_BATCH = 'max_steps_per_batch'
    EXECUTAR_BUILD_DOTNET = 'executar_build_dotnet'
    BUILD_ERRORS = 'build_errors'
    BUILD_RESULT = 'build_result'
    WORKFLOW_MODE = 'workflow_mode'
    EPIC_ID = 'epic_id'
    TASK_IDS = 'task_ids'
    EPIC_IDS = 'epic_ids'
    EPICS_CREATED = 'epics_created'

class JobActions:
    APPROVE = 'approve'
    REJECT = 'reject'

class StartAnalysisPayload(BaseModel):
    repo_name_modernizado: Optional[str] = None
    branch_name_modernizado: Optional[str] = None
    projeto: str
    analysis_type: Any
    instrucoes_extras: Optional[str] = None
    usar_rag: bool = False
    gerar_relatorio_apenas: bool = False
    gerar_novo_relatorio: bool = True
    model_name: Optional[str] = None
    arquivos_especificos: Optional[List[str]] = None
    analysis_name: Optional[str] = None
    repository_type: str
    repo_name_original: Optional[str] = None
    branch_name_original: Optional[str] = None
    retornar_lista_arquivos: bool = False
    modo_adicao_incremental: bool = False
    usuario_executor: Optional[str] = None
    executar_steps_incrementalmente: bool = False
    max_steps_per_batch: Optional[int] = Field(3, description="Número máximo de steps por batch na execução incremental")
    executar_build_dotnet: bool = Field(False, description="Se True, executa o build do projeto .NET após o commit e retorna os erros de compilação, se houver.")
    workflow_mode: Optional[str] = Field(None, description="Modo do workflow: 'code_generation' ou 'epic_task_creation'.")

    @validator('branch_name_modernizado', always=True)
    def branch_name_conditional(cls, v, values):
        workflow_mode = values.get('workflow_mode')
        if workflow_mode == 'code_generation' and (v is None or v == ''):
            raise ValueError("branch_name_modernizado é obrigatório quando workflow_mode é 'code_generation'.")
        return v

    @root_validator(pre=True)
    def remove_fields_for_epic_task_creation(cls, values):
        workflow_mode = values.get('workflow_mode')
        if workflow_mode == 'epic_task_creation':
            values['branch_name_modernizado'] = None
            values['repo_name_original'] = None
            values['branch_name_original'] = None
        return values
