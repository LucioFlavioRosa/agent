from fastapi import HTTPException
from models import JobStatus, JobFields

class JobValidationService:
    """Serviço responsável por validações relacionadas a jobs."""
    
    def validate_job_for_approval(self, job: dict, job_id: str) -> None:
        """Valida se o job está em estado apropriado para aprovação."""
        if not job or job.get(JobFields.STATUS) != JobStatus.PENDING_APPROVAL:
            raise HTTPException(
                status_code=400, 
                detail="Job não encontrado ou não está aguardando aprovação."
            )
    
    def validate_job_exists(self, job: dict, job_id: str) -> None:
        """Valida se o job existe."""
        if not job:
            raise HTTPException(
                status_code=404, 
                detail="Job ID não encontrado ou expirado"
            )
    
    def validate_analysis_exists(self, analysis_name: str, analysis_service) -> str:
        """Valida se a análise existe e retorna o job_id."""
        job_id = analysis_service.find_job_by_analysis_name(analysis_name)
        if not job_id:
            raise HTTPException(
                status_code=404, 
                detail=f"Análise com nome '{analysis_name}' não encontrada"
            )
        return job_id
    
    def get_report_from_job(self, job: dict, job_id: str) -> str:
        """Extrai e valida relatório do job."""
        report = job.get(JobFields.DATA, {}).get(JobFields.ANALYSIS_REPORT)
        if not report:
            raise HTTPException(
                status_code=404, 
                detail=f"Relatório não encontrado para o job {job_id}. Status do job: {job.get('status')}. Verifique se o job foi executado com 'gerar_relatorio_apenas=True' ou se o relatório foi gerado com sucesso."
            )
        return report
