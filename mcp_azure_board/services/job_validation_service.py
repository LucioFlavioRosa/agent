from typing import Dict, Any, Optional
from models import JobFields, JobStatus

class JobValidationService:
    def validate_job_exists(self, job: Optional[Dict[str, Any]], job_id: str) -> None:
        if not job:
            raise ValueError(f"Job {job_id} não encontrado.")

    def validate_job_for_approval(self, job: Dict[str, Any], job_id: str) -> None:
        if job.get(JobFields.STATUS) != JobStatus.PENDING_APPROVAL:
            raise ValueError(f"Job {job_id} não está aguardando aprovação.")

    def validate_analysis_exists(self, analysis_name: str, analysis_service) -> str:
        job_id = analysis_service.get_job_id_by_analysis_name(analysis_name)
        if not job_id:
            raise ValueError(f"Análise '{analysis_name}' não encontrada.")
        return job_id

    def get_report_from_job(self, job: Dict[str, Any], job_id: Optional[str]) -> Optional[str]:
        report = job.get(JobFields.DATA, {}).get(JobFields.ANALYSIS_REPORT)
        if not report:
            raise ValueError(f"Relatório não encontrado para job {job_id}.")
        return report
