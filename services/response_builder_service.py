from typing import Dict, Any, List, Optional
from models import JobFields
from pydantic import BaseModel

class FinalStatusResponse(BaseModel):
    job_id: str
    status: str
    summary: Optional[List[Dict]] = None
    error_details: Optional[str] = None
    analysis_report: Optional[str] = None
    diagnostic_logs: Optional[str] = None
    report_blob_url: Optional[str] = None
    build_errors: Optional[List[str]] = None
    epicos: Optional[List[Any]] = None
    cards_criados: Optional[List[Dict]] = None
    cards_creation_errors: Optional[List[Any]] = None
    tarefas_criadas: Optional[List[Dict]] = None
    tarefas_creation_errors: Optional[List[Any]] = None

class ResponseBuilderService:
    def __init__(self, pr_extractor, logging_service):
        self.pr_extractor = pr_extractor
        self.logging_service = logging_service
         
    def build_completed_response(self, job_id: str, job: Dict[str, Any], blob_url: Optional[str]) -> FinalStatusResponse:
        data = job.get(JobFields.DATA, {})
        commit_details = data.get('commit_details', [])
        summary = []
        build_errors_aggregate = []
        for idx, commit in enumerate(commit_details):
            pr_url = commit.get('pr_url')
            branch_name = commit.get('branch_name')
            arquivos_modificados = commit.get('arquivos_modificados', [])
            build_result = commit.get('build_result') if 'build_result' in commit else None
            commit_url = commit.get('commit_url') if 'commit_url' in commit else None
            build_errors = commit.get('build_errors') if 'build_errors' in commit else None
            if build_errors:
                if isinstance(build_errors, list):
                    build_errors_aggregate.extend(build_errors)
                else:
                    build_errors_aggregate.append(str(build_errors))
            summary.append({
                "pull_request_url": pr_url if pr_url else None,
                "branch_name": branch_name,
                "arquivos_modificados": arquivos_modificados,
                "build_result": build_result,
                "commit_url": commit_url
            })
        analysis_report = data.get(JobFields.ANALYSIS_REPORT, None)
        diagnostic_logs = data.get('diagnostic_logs', None)
        error_details = job.get('error_details', None)
        epicos = None
        cards_criados = None
        cards_creation_errors = None
        tarefas_criadas = None
        tarefas_creation_errors = None
        if data.get('gerar_epicos', False):
            epicos = data.get('epicos', None)
            cards_criados = data.get('cards_criados', None)
            cards_creation_errors = data.get('cards_creation_errors', None)
        if data.get('gerar_tarefas', False):
            tarefas_criadas = data.get('tarefas_criadas', None)
            tarefas_creation_errors = data.get('tarefas_creation_errors', None)
        return FinalStatusResponse(
            job_id=job_id,
            status=job.get(JobFields.STATUS, "completed"),
            summary=summary,
            error_details=error_details,
            analysis_report=analysis_report,
            diagnostic_logs=diagnostic_logs,
            report_blob_url=blob_url,
            build_errors=build_errors_aggregate if build_errors_aggregate else None,
            epicos=epicos,
            cards_criados=cards_criados,
            cards_creation_errors=cards_creation_errors,
            tarefas_criadas=tarefas_criadas,
            tarefas_creation_errors=tarefas_creation_errors
        )
    def build_failed_response(self, job_id: str, job: Dict[str, Any]) -> FinalStatusResponse:
        data = job.get(JobFields.DATA, {})
        error_details = job.get('error_details', None)
        analysis_report = data.get(JobFields.ANALYSIS_REPORT, None)
        diagnostic_logs = data.get('diagnostic_logs', None)
        blob_url = data.get(JobFields.REPORT_BLOB_URL, None)
        build_errors = data.get('build_errors', None)
        tarefas_criadas = data.get('tarefas_criadas', None)
        tarefas_creation_errors = data.get('tarefas_creation_errors', None)
        return FinalStatusResponse(
            job_id=job_id,
            status=job.get(JobFields.STATUS, "failed"),
            summary=None,
            error_details=error_details,
            analysis_report=analysis_report,
            diagnostic_logs=diagnostic_logs,
            report_blob_url=blob_url,
            build_errors=build_errors,
            tarefas_criadas=tarefas_criadas,
            tarefas_creation_errors=tarefas_creation_errors
        )
