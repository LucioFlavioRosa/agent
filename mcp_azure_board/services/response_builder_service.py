from models import FinalStatusResponse

class ResponseBuilderService:
    def build_completed_response(self, job_id, job, blob_url=None):
        job_data = job.get('data', {})
        analysis_report = job_data.get('analysis_report')
        return FinalStatusResponse(
            job_id=job_id,
            status='completed',
            report_blob_url=blob_url,
            analysis_report=analysis_report
        )

    def build_failed_response(self, job_id, job):
        job_data = job.get('data', {})
        error_details = job_data.get('error_details', 'Erro desconhecido.')
        return FinalStatusResponse(
            job_id=job_id,
            status='failed',
            error_details=error_details
        )
