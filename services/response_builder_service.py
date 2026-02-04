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

class ResponseBuilderService:
    def __init__(self, pr_extractor, logging_service):
        self.pr_extractor = pr_extractor
        self.logging_service = logging_service
    
    def build_completed_response(self, job_id: str, job: Dict[str, Any], blob_url: Optional[str]) -> FinalStatusResponse:
        data = job.get('data', {})
        commit_details = data.get('commit_details', [])
        summary = []
        build_errors_aggregate = []
        for idx, commit in enumerate(commit_details):
            commit_summary, build_errors = self._process_commit_detail(commit)
            summary.append(commit_summary)
            if build_errors:
                if isinstance(build_errors, list):
                    build_errors_aggregate.extend(build_errors)
                else:
                    build_errors_aggregate.append(str(build_errors))
        analysis_report = data.get('analysis_report', None)
        diagnostic_logs = data.get('diagnostic_logs', None)
        error_details = job.get('error_details', None)
        return FinalStatusResponse(
            job_id=job_id,
            status=job.get('status', "completed"),
            summary=summary,
            error_details=error_details,
            analysis_report=analysis_report,
            diagnostic_logs=diagnostic_logs,
            report_blob_url=blob_url,
            build_errors=build_errors_aggregate if build_errors_aggregate else None
        )
    
    def build_failed_response(self, job_id: str, job: Dict[str, Any]) -> FinalStatusResponse:
        data = job.get('data', {})
        error_details = job.get('error_details', None)
        analysis_report = data.get('analysis_report', None)
        diagnostic_logs = data.get('diagnostic_logs', None)
        blob_url = data.get('report_blob_url', None)
        build_errors = data.get('build_errors', None)
        return FinalStatusResponse(
            job_id=job_id,
            status=job.get('status', "failed"),
            summary=None,
            error_details=error_details,
            analysis_report=analysis_report,
            diagnostic_logs=diagnostic_logs,
            report_blob_url=blob_url,
            build_errors=build_errors
        )
    
    def _process_commit_detail(self, commit: Dict[str, Any]) -> (Dict[str, Any], Optional[List[str]]):
        pr_url = commit.get('pr_url')
        branch_name = commit.get('branch_name')
        arquivos_modificados = commit.get('arquivos_modificados', [])
        build_result = commit.get('build_result') if 'build_result' in commit else None
        commit_url = commit.get('commit_url') if 'commit_url' in commit else None
        build_errors = commit.get('build_errors') if 'build_errors' in commit else None
        commit_summary = {
            "pull_request_url": pr_url if pr_url else None,
            "branch_name": branch_name,
            "arquivos_modificados": arquivos_modificados,
            "build_result": build_result,
            "commit_url": commit_url
        }
        return commit_summary, build_errors
