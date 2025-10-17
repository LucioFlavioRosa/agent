class BlobStorageService:
    def __init__(self, uploader, reader, job_tracker):
        self.uploader = uploader
        self.reader = reader
        self.job_tracker = job_tracker
    def upload_report(self, report_text, projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name):
        print(f"[DEBUG][BlobStorageService.upload_report] Parâmetros recebidos: projeto={projeto}, analysis_type={analysis_type}, repository_type={repository_type}, repo_name={repo_name}, branch_name={branch_name}, analysis_name={analysis_name}")
        blob_path = None
        try:
            from tools.blob_report_path_builder import build_report_blob_path
            blob_path = build_report_blob_path(projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name)
            print(f"[DEBUG][BlobStorageService.upload_report] blob_path construído: {blob_path}")
        except Exception as e:
            print(f"[BlobStorageService] Erro ao construir blob_path: {e}")
            raise
        url = self.uploader(report_text, projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name)
        return url
    def read_report(self, projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name):
        return self.reader(projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name)
    def update_job_tracker(self, report_blob_url, job_id):
        self.job_tracker(report_blob_url, job_id)
