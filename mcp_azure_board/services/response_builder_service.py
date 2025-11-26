from typing import Dict, Any
from models import JobStatus

class ResponseBuilderService:
    """
    Serviço responsável por construir respostas de status para jobs do MCP Azure Board.
    Foca em jobs de board, sem campos de PR, build, etc.
    """
    def build_completed_response(self, job_id: str, job: Dict[str, Any], report_blob_url: str = None) -> Dict[str, Any]:
        return {
            "job_id": job_id,
            "status": JobStatus.COMPLETED,
            "report_blob_url": report_blob_url,
            "analysis_report": job.get("data", {}).get("analysis_report"),
            "error_details": job.get("data", {}).get("error_details"),
            "summary": job.get("data", {}).get("summary"),
            "diagnostic_logs": job.get("data", {}).get("diagnostic_logs")
        }

    def build_failed_response(self, job_id: str, job: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "job_id": job_id,
            "status": JobStatus.FAILED,
            "error_details": job.get("data", {}).get("error_details"),
            "analysis_report": job.get("data", {}).get("analysis_report"),
            "diagnostic_logs": job.get("data", {}).get("diagnostic_logs")
        }
