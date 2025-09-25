from typing import Optional
from domain.interfaces.blob_storage_interface import IBlobStorageService
from tools.blob_report_uploader import upload_report_to_blob
from tools.blob_report_reader import read_report_from_blob

class BlobStorageService(IBlobStorageService):
    def upload_report(self, report_text: str, projeto: str, analysis_type: str, 
                     repository_type: str, repo_name: str, branch_name: str, 
                     analysis_name: str) -> str:
        return upload_report_to_blob(
            report_text, projeto, analysis_type, repository_type, 
            repo_name, branch_name, analysis_name
        )
    
    def read_report(self, projeto: str, analysis_type: str, repository_type: str, 
                   repo_name: str, branch_name: str, analysis_name: str) -> Optional[str]:
        try:
            return read_report_from_blob(
                projeto, analysis_type, repository_type, 
                repo_name, branch_name, analysis_name
            )
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"Erro ao ler relatório do Blob Storage: {e}")
            return None