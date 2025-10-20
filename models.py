from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

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

class EpicoCard(BaseModel):
    id: str
    titulo: str
    objetivo_negocio: str
    criterios_aceite: str
    perfis_envolvidos: str
    estimativa_esforco: str

class TarefaCard(BaseModel):
    id: str
    titulo_tarefa: str
    descricao_tarefa: str
    epico_id: str
    estimativa_tempo: str
    criterios_aceite: str
    epico_nome: Optional[str] = None

class EpicoResponse(BaseModel):
    job_id: str
    epicos: List[EpicoCard]
    cards_criados: Optional[List[Dict[str, Any]]] = None

class TarefaResponse(BaseModel):
    job_id: str
    tarefas: List[TarefaCard]
    tarefas_criadas: Optional[List[Dict[str, Any]]] = None

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
    TRANSCRICAO_REUNIAO = 'transcricao_reuniao'
    GERAR_EPICOS = 'gerar_epicos'
    CRIAR_CARDS_AZURE = 'criar_cards_azure'
    AZURE_PROJECT_NAME = 'azure_project_name'
    CARDS_CRIADOS = 'cards_criados'
    CARDS_CREATION_ERRORS = 'cards_creation_errors'
    GERAR_TAREFAS = 'gerar_tarefas'
    EPICOS_APROVADOS = 'epicos_aprovados'
    TAREFAS_CRIADAS = 'tarefas_criadas'
    TAREFAS_CREATION_ERRORS = 'tarefas_creation_errors'

class JobActions:
    APPROVE = 'approve'
    REJECT = 'reject'

class StartAnalysisPayload(BaseModel):
    repo_name_modernizado: str
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
    transcricao_reuniao: Optional[str] = None
    gerar_epicos: bool = False
    criar_cards_azure: bool = False
    azure_project_name: Optional[str] = None
    gerar_tarefas: bool = False
    epicos_aprovados: Optional[List[str]] = None
