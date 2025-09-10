from abc import ABC, abstractmethod
from typing import Optional

class IBlobStorageService(ABC):
    @abstractmethod
    def upload_report(self, report_text: str, projeto: str, analysis_type: str, 
                     repository_type: str, repo_name: str, branch_name: str, 
                     analysis_name: str) -> str:
        pass
    
    @abstractmethod
    def read_report(self, projeto: str, analysis_type: str, repository_type: str, 
                   repo_name: str, branch_name: str, analysis_name: str) -> Optional[str]:
        pass