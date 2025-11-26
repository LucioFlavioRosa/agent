import os
from typing import Dict, Any, Optional
from services.blob_storage_service import BlobStorageService

class ReportHandler:
    def __init__(self, blob_storage: Optional[BlobStorageService] = None, cache_service=None):
        self.blob_storage = blob_storage or BlobStorageService()
        self.cache_service = cache_service

    def extract_report_text(self, step_result: Dict[str, Any]) -> Optional[str]:
        if not step_result:
            return None
        if isinstance(step_result, dict):
            report = step_result.get('report') or step_result.get('relatorio')
            if report:
                return report
            if 'resultado' in step_result and isinstance(step_result['resultado'], dict):
                return step_result['resultado'].get('report') or step_result['resultado'].get('relatorio')
        if isinstance(step_result, str):
            return step_result
        return None

    def save_report_to_blob(self, job_id: str, job_info: Dict[str, Any], report_text: str) -> str:
        projeto = job_info['data'].get('projeto')
        analysis_type = job_info['data'].get('original_analysis_type')
        repository_type = job_info['data'].get('repository_type')
        repo_name = job_info['data'].get('repo_name')
        branch_name = job_info['data'].get('branch_name_modernizado')
        analysis_name = job_info['data'].get('analysis_name')
        return self.blob_storage.upload_report(
            report_text, projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name
        )
