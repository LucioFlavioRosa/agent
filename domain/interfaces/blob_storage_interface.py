from typing import Optional

class IBlobStorageService:
    def upload_report(self, report_text: str, projeto: str, analysis_type: str, repository_type: str, repo_name: str, branch_name: str, analysis_name: str, usuario_executor: Optional[str] = None) -> str:
        raise NotImplementedError

    def read_report(self, projeto: str, analysis_type: str, repository_type: str, repo_name: str, branch_name: str, analysis_name: str, usuario_executor: Optional[str] = None) -> Optional[str]:
        raise NotImplementedError
