class ReportHandler:
    def __init__(self, blob_storage):
        self.blob_storage = blob_storage

    def extract_report_text(self, step_result):
        if not step_result:
            return ''
        return step_result.get('report_text', '') or step_result.get('analysis_report', '') or ''

    def save_report_to_blob(self, job_id, job_info, report_text, report_generated_by_agent=False):
        url = self.blob_storage.upload_report(job_id, report_text)
        if url and report_generated_by_agent:
            self.blob_storage.update_job_tracker(url, job_id)
        return url
