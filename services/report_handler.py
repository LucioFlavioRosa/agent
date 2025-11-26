class ReportHandler:
    def __init__(self, blob_storage, cache_service=None):
        self.blob_storage = blob_storage
        self.cache_service = cache_service

    def extract_report_text(self, step_result):
        # Genérico: espera 'report' ou 'analysis_report' no dict
        return step_result.get('report') or step_result.get('analysis_report')

    def save_report_to_blob(self, job_id, job_info, report_text):
        # Plataforma agnóstica: delega ao blob_storage
        return self.blob_storage.save_report(job_id, job_info, report_text)
