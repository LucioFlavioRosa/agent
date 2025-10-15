from typing import Dict, Any, List, Optional
from models import JobFields

class FinalStatusResponse:
    def __init__(self, job_id: str, status: str, summary: Optional[List[Dict]] = None, error_details: Optional[str] = None, analysis_report: Optional[str] = None, diagnostic_logs: Optional[str] = None, report_blob_url: Optional[str] = None, build_errors: Optional[List[str]] = None):
        self.job_id = job_id
        self.status = status
        self.summary = summary
        self.error_details = error_details
        self.analysis_report = analysis_report
        self.diagnostic_logs = diagnostic_logs
        self.report_blob_url = report_blob_url
        self.build_errors = build_errors

    def dict(self):
        return {
            "job_id": self.job_id,
            "status": self.status,
            "summary": self.summary,
            "error_details": self.error_details,
            "analysis_report": self.analysis_report,
            "diagnostic_logs": self.diagnostic_logs,
            "report_blob_url": self.report_blob_url,
            "build_errors": self.build_errors
        }

class ResponseBuilderService:
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
            # Agrega build_errors para resposta geral
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
        return FinalStatusResponse(
            job_id=job_id,
            status=job.get(JobFields.STATUS, "completed"),
            summary=summary,
            error_details=error_details,
            analysis_report=analysis_report,
            diagnostic_logs=diagnostic_logs,
            report_blob_url=blob_url,
            build_errors=build_errors_aggregate if build_errors_aggregate else None
        )
    def build_failed_response(self, job_id: str, job: Dict[str, Any]) -> FinalStatusResponse:
        data = job.get(JobFields.DATA, {})
        error_details = job.get('error_details', None)
        analysis_report = data.get(JobFields.ANALYSIS_REPORT, None)
        diagnostic_logs = data.get('diagnostic_logs', None)
        blob_url = data.get(JobFields.REPORT_BLOB_URL, None)
        build_errors = data.get('build_errors', None)
        return FinalStatusResponse(
            job_id=job_id,
            status=job.get(JobFields.STATUS, "failed"),
            summary=None,
            error_details=error_details,
            analysis_report=analysis_report,
            diagnostic_logs=diagnostic_logs,
            report_blob_url=blob_url,
            build_errors=build_errors
        )
