from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class EpicCreationPayload(BaseModel):
    transcricao_reuniao: str = Field(..., description="Transcrição da reunião para geração de épicos")
    criar_epicos_azure: bool = Field(False, description="Se True, após aprovação, cria os épicos no Azure DevOps Board")

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
    ANALYSIS_TYPE = 'analysis_type'
    INSTRUCOES_EXTRAS = 'instrucoes_extras'
    MODEL_NAME = 'model_name'
    USAR_RAG = 'usar_rag'
    GERAR_RELATORIO_APENAS = 'gerar_relatorio_apenas'
    ANALYSIS_NAME = 'analysis_name'
    REPOSITORY_TYPE = 'repository_type'
    ANALYSIS_REPORT = 'analysis_report'
    REPORT_BLOB_URL = 'report_blob_url'
    INSTRUCOES_EXTRAS_APROVACAO = 'instrucoes_extras_aprovacao'
    PAUSED_AT_STEP = 'paused_at_step'
    SUCCESS = 'success'
    ORGANIZATION = 'organization'
    PROJECT = 'project'
    EPIC_ID = 'epic_id'
    FEATURE_ID = 'feature_id'
    TASK_ID = 'task_id'
    BUILD_ERRORS = 'build_errors'
    EPICOS_CRIADOS = 'epicos_criados'
    FEATURES_CRIADAS = 'features_criadas'
    TAREFAS_CRIADAS = 'tarefas_criadas'
    FEATURES_CRIADAS_ERRO = 'features_criadas_erro'
    TAREFAS_CRIADAS_ERRO = 'tarefas_criadas_erro'
    TASK_DISCUSSION_UPDATE_RESULT = 'task_discussion_update_result'
    EXECUTAR_STEPS_INCREMENTALMENTE = 'executar_steps_incrementalmente'
    MAX_STEPS_PER_BATCH = 'max_steps_per_batch'
    STEP_BATCHES = 'step_batches'
    CURRENT_BATCH_INDEX = 'current_batch_index'
    BATCH_RESULTS = 'batch_results'

class JobActions:
    APPROVE = 'approve'
    REJECT = 'reject'

class ValidAnalysisTypes(str, Enum):
    CRIACAO_EPICOS_AZURE_DEVOPS = 'criacao_epicos_azure_devops'
    CRIACAO_TAREFAS_AZURE_DEVOPS = 'criacao_tarefas_azure_devops'
    REVISOR_TAREFAS = 'revisor_tarefas'
    CRIACAO_FEATURES_AZURE_DEVOPS = 'criacao_features_azure_devops'
