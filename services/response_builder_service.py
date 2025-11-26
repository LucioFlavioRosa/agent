from models import FinalStatusResponse

class ResponseBuilderService:
    def build_completed_response(self, job_id, job, blob_url):
        return FinalStatusResponse(
            job_id=job_id,
            status='completed',
            report_blob_url=blob_url,
            analysis_report=job.get('data', {}).get('analysis_report'),
            build_errors=job.get('data', {}).get('build_errors')
        )

    def build_failed_response(self, job_id, job):
        return FinalStatusResponse(
            job_id=job_id,
            status='failed',
            error_details=job.get('data', {}).get('error_details'),
            report_blob_url=job.get('data', {}).get('report_blob_url'),
            build_errors=job.get('data', {}).get('build_errors')
        )
