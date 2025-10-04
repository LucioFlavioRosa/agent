from tools.blob_report_uploader import upload_report_to_blob

class ReportHandler:
    def __init__(self, blob_storage):
        self.blob_storage = blob_storage

    # ... outros métodos ...

    def save_report_to_blob(self, job_id: str, job_info: dict, report_text: str, report_generated_by_agent: bool = False) -> tuple[str, str]:
        """
        Salva o relatório no Blob Storage e retorna a URL e o blob path.
        """
        projeto = job_info['data']['projeto']
        analysis_type = job_info['data']['original_analysis_type']
        repository_type = job_info['data']['repository_type']
        repo_name = job_info['data']['repo_name']
        branch_name = job_info['data']['branch_name']
        analysis_name = job_info['data']['analysis_name']
        
        blob_url, blob_path = upload_report_to_blob(
            report_text, projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name
        )
        
        job_info['data']['report_blob_url'] = blob_url
        job_info['data']['report_blob_path'] = blob_path  # SALVA O BLOB PATH NO JOB
        
        print(f"[{job_id}] Relatório salvo no Blob Storage: {blob_url}")
        print(f"[{job_id}] Blob path: {blob_path}")
        
        return blob_url, blob_path
