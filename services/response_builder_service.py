from typing import List, Dict, Any, Optional
from models import JobStatus, JobFields
from fastapi import HTTPException
from pydantic import BaseModel
import time
from models import JobStatus, JobFields, FinalStatusResponse, PullRequestSummary

class ResponseBuilderService:
    
    def __init__(self, pr_extractor_service, logging_service):
        self.pr_extractor_service = pr_extractor_service
        self.logging_service = logging_service
    
    def build_completed_response(self, job_id: str, job: dict, blob_url: Optional[str]) -> FinalStatusResponse:
        job_data = job.get(JobFields.DATA, {})
        gerar_relatorio_apenas = job_data.get(JobFields.GERAR_RELATORIO_APENAS, False)
        print(f"[{job_id}] [ResponseBuilder] Construindo resposta - modo relatório: {gerar_relatorio_apenas}")
        if gerar_relatorio_apenas:
            return self._build_report_only_response(job_id, job_data, blob_url)
        return self._build_standard_response(job_id, job, blob_url)
    
    def _build_report_only_response(self, job_id: str, job_data: dict, blob_url: Optional[str]) -> FinalStatusResponse:
        analysis_report = job_data.get(JobFields.ANALYSIS_REPORT)
        final_blob_url = blob_url or job_data.get(JobFields.REPORT_BLOB_URL)
        if not analysis_report:
            raise HTTPException(
                status_code=500, 
                detail=f"[{job_id}] ERRO INTERNO: Relatório ausente no modo report_only após finalização do workflow."
            )
        return FinalStatusResponse(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            analysis_report=analysis_report,
            report_blob_url=final_blob_url
        )
    
    def _build_standard_response(self, job_id: str, job: dict, blob_url: Optional[str]) -> FinalStatusResponse:
        job_data = job.get(JobFields.DATA, {})
        summary_list = self.pr_extractor_service.extract_pull_requests(job_id, job_data)
        self.logging_service.log_completed_job(job_id, job_data, summary_list, blob_url)
        final_blob_url = blob_url or job_data.get(JobFields.REPORT_BLOB_URL)
        logs = job_data.get(JobFields.DIAGNOSTIC_LOGS)
        build_errors = job_data.get(JobFields.BUILD_ERRORS)
        return FinalStatusResponse(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            summary=summary_list,
            diagnostic_logs=logs,
            report_blob_url=final_blob_url,
            build_errors=build_errors if build_errors else None
        )
    
    def build_failed_response(self, job_id: str, job: dict) -> FinalStatusResponse:
        job_data = job.get(JobFields.DATA, {})
        logs = job_data.get(JobFields.DIAGNOSTIC_LOGS)
        blob_url = job_data.get(JobFields.REPORT_BLOB_URL)
        self.logging_service.log_failed_job(job_id, job_data, blob_url)
        return FinalStatusResponse(
            job_id=job_id,
            status=JobStatus.FAILED,
            error_details=job.get(JobFields.ERROR_DETAILS, "Nenhum detalhe de erro encontrado."),
            diagnostic_logs=logs,
            report_blob_url=blob_url
        )
