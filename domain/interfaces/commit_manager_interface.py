from abc import ABC, abstractmethod
from typing import Dict, Any

class ICommitManager(ABC):
    @abstractmethod
    def execute_commits(self, job_id: str, job_info: Dict[str, Any], dados_finais_formatados: Dict[str, Any], repository_type: str, repo_name: str) -> None:
        pass
    
    @abstractmethod
    def format_final_data(self, dados_preenchidos: Dict[str, Any]) -> Dict[str, Any]:
        pass