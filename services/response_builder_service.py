from typing import Any, Dict, Optional, List
from models import JobFields, JobStatus
from services.response_builder_service import FinalStatusResponse

class ResponseBuilderService:
    def build_completed_response(self, job_id: str, job: Dict[str, Any], blob_url: Optional[str]) -> FinalStatusResponse:
        job_data = job.get(JobFields.DATA, {})
        build_errors = job_data.get(JobFields.BUILD_ERRORS)
        return FinalStatusResponse(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            report_blob_url=blob_url,
            build_errors=build_errors
        )
    def build_failed_response(self, job_id: str, job: Dict[str, Any]) -> FinalStatusResponse:
        job_data = job.get(JobFields.DATA, {})
        build_errors = job_data.get(JobFields.BUILD_ERRORS)
        return FinalStatusResponse(
            job_id=job_id,
            status=JobStatus.FAILED,
            report_blob_url=job_data.get(JobFields.REPORT_BLOB_URL),
            build_errors=build_errors
        )
