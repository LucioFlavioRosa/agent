from pydantic import BaseModel, Field, validator, ValidationError
from typing import List, Dict, Any, Optional, Literal
from enum import Enum

class JobFields(BaseModel):
    job_id: str
    status: str
    repo_name: Optional[str] = None
    branch_name: Optional[str] = None
    agent_type: Optional[str] = None
    arquivos_especificos: Optional[list] = None
    instrucoes_extras: Optional[str] = None
    analysis_report: Optional[str] = None
    report_blob_url: Optional[str] = None
    projeto: Optional[str] = None
    analysis_name: Optional[str] = None
    gerar_relatorio_apenas: Optional[bool] = None
    retornar_lista_arquivos: Optional[bool] = None
    usuario_executor: str = Field(..., description="Email do usuário executor (obrigatório)")

    @validator('usuario_executor')
    def validate_usuario_executor(cls, v):
        if not v or '@' not in v:
            raise ValueError("usuario_executor deve ser um email válido.")
        return v

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

class JobActions:
    APPROVE = 'approve'
    REJECT = 'reject'
