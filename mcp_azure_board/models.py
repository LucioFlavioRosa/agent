from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from enum import Enum

class PullRequestSummary(BaseModel):
    pull_request_url: str
    branch_name: str
    arquivos_modificados: List[str]

class FinalStatusResponse(BaseModel):
    job_id: str
    status: str
    summary: Optional[List[PullRequestSummary]] = None
    error_details: Optional[str] = None
    analysis_report: Optional[str] = None
    report_blob_url: Optional[str] = None

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
    PROJETO = 'projeto'
    INSTRUCOES_EXTRAS = 'instrucoes_extras'
    MODEL_NAME = 'model_name'
    USAR_RAG = 'usar_rag'
    GERAR_RELATORIO_APENAS = 'gerar_relatorio_apenas'
    ARQUIVOS_ESPECIFICOS = 'arquivos_especificos'
    ANALYSIS_NAME = 'analysis_name'
    REPOSITORY_TYPE = 'repository_type'
    ANALYSIS_REPORT = 'analysis_report'
    REPORT_BLOB_URL = 'report_blob_url'
    INSTRUCOES_EXTRAS_APROVACAO = 'instrucoes_extras_aprovacao'
    PAUSED_AT_STEP = 'paused_at_step'
    RETORNAR_LISTA_ARQUIVOS = 'retornar_lista_arquivos'
    USUARIO_EXECUTOR = 'usuario_executor'
    EXECUTAR_STEPS_INCREMENTALMENTE = 'executar_steps_incrementalmente'
    STEP_BATCHES = 'step_batches'
    CURRENT_BATCH_INDEX = 'current_batch_index'
    BATCH_RESULTS = 'batch_results'
    MAX_STEPS_PER_BATCH = 'max_steps_per_batch'

class JobActions:
    APPROVE = 'approve'
    REJECT = 'reject'

class ValidAnalysisTypes(str, Enum):
    CRIACAO_EPICOS_AZURE_DEVOPS = 'criacao_epicos_azure_devops'
    CRIACAO_TAREFAS_AZURE_DEVOPS = 'criacao_tarefas_azure_devops'
    REVISOR_TAREFAS = 'revisor_tarefas'
    CRIACAO_FEATURES_AZURE_DEVOPS = 'criacao_features_azure_devops'
