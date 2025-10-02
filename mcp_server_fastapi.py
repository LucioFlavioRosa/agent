import json
import uuid
import time
import traceback

from fastapi import FastAPI, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, Literal, List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware

from services.dependency_container import DependencyContainer
from services.workflow_registry_service import WorkflowRegistryService

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

class JobActions:
    APPROVE = 'approve'
    REJECT = 'reject'

container = DependencyContainer()
workflow_registry_service = container.get_workflow_registry_service()
ValidAnalysisTypes = workflow_registry_service.get_valid_analysis_types()

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

class FinalStatusResponse(BaseModel):
    job_id: str
    status: str
    summary: Optional[List[PullRequestSummary]] = Field(None)
    error_details: Optional[str] = Field(None)
    analysis_report: Optional[str] = Field(None)
    diagnostic_logs: Optional[Dict[str, Any]] = Field(None)
    report_blob_url: Optional[str] = Field(None)

class ReportResponse(BaseModel):
    job_id: str
    analysis_report: Optional[str]
    report_blob_url: Optional[str] = Field(None)

class AnalysisByNameResponse(BaseModel):
    job_id: str
    analysis_name: str
    analysis_report: Optional[str]
    report_blob_url: Optional[str] = Field(None)

def _validate_and_normalize_gitlab_repo_name(repo_name: str) -> str:
    repo_name = repo_name.strip()

    try:
        project_id = int(repo_name)
        print(f"GitLab Project ID detectado: {project_id}. Usando formato numérico para máxima robustez.")
        return str(project_id)
    except ValueError:
        pass

    if '/' in repo_name:
        parts = [p for p in repo_name.split('/') if p]

        if len(parts) >= 2:
            normalized_path = '/'.join(parts)
            print(f"GitLab path completo detectado: {normalized_path}. RECOMENDAÇÃO: Use o Project ID numérico para máxima robustez contra renomeações.")
            return normalized_path
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Path GitLab inválido: '{repo_name}'. Esperado pelo menos 'namespace/projeto'. Exemplo: 'meugrupo/meuprojeto' ou use o Project ID numérico (recomendado)."
            )

    raise HTTPException(
        status_code=400,
        detail=f"Formato de repositório GitLab inválido: '{repo_name}'. Use o Project ID numérico (RECOMENDADO para máxima robustez) ou o path completo 'namespace/projeto'. Exemplos: Project ID: '123456', Path: 'meugrupo/meuprojeto'"
    )

def _normalize_repo_name_by_type(repo_name: str, repository_type: str) -> str:
    if repository_type == 'gitlab':
        normalized = _validate_and_normalize_gitlab_repo_name(repo_name)
        print(f"GitLab - Repo original: '{repo_name}', normalizado: '{normalized}'")
        return normalized
    return repo_name

def _generate_analysis_name(provided_name: Optional[str], job_id: str) -> str:
    if provided_name:
        return provided_name

    analysis_name = f"analysis-{str(uuid.uuid4())[:8]}"
    print(f"[{job_id}] Nome de análise gerado automaticamente: {analysis_name}")
    return analysis_name

def _create_initial_job_data(payload: StartAnalysisPayload, normalized_repo_name: str, analysis_name: str) -> dict:
    return {
        JobFields.STATUS: JobStatus.STARTING,
        JobFields.DATA: {
            JobFields.REPO_NAME: normalized_repo_name,
            JobFields.ORIGINAL_REPO_NAME: payload.repo_name_modernizado,
            JobFields.PROJETO: payload.projeto,
            JobFields.BRANCH_NAME: payload.branch_name_modernizado,
            JobFields.ORIGINAL_ANALYSIS_TYPE: payload.analysis_type.value,
            JobFields.INSTRUCOES_EXTRAS: payload.instrucoes_extras,
            JobFields.MODEL_NAME: payload.model_name,
            JobFields.USAR_RAG: payload.usar_rag,
            JobFields.GERAR_RELATORIO_APENAS: payload.gerar_relatorio_apenas,
            JobFields.GERAR_NOVO_RELATORIO: payload.gerar_novo_relatorio,
            JobFields.ARQUIVOS_ESPECIFICOS: payload.arquivos_especificos,
            JobFields.ANALYSIS_NAME: analysis_name,
            JobFields.REPOSITORY_TYPE: payload.repository_type,
            JobFields.REPO_NAME_MODERNIZADO: payload.repo_name_modernizado,
            JobFields.BRANCH_NAME_MODERNIZADO: payload.branch_name_modernizado,
            JobFields.REPO_NAME_ORIGINAL: payload.repo_name_original,
            JobFields.BRANCH_NAME_ORIGINAL: payload.branch_name_original,
            JobFields.RETORNAR_LISTA_ARQUIVOS: payload.retornar_lista_arquivos,
            JobFields.MODO_ADICAO_INCREMENTAL: payload.modo_adicao_incremental
        },
        JobFields.ERROR_DETAILS: None
    }

# ... (restante do arquivo permanece inalterado)
