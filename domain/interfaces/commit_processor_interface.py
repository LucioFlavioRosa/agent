from abc import ABC, abstractmethod
from typing import Dict, Any, List

class ICommitProcessor(ABC):
    @abstractmethod
    def process_commits(self, repo: Any, dados_finais_formatados: Dict[str, Any], 
                      branch_base_para_pr: str, repository_type: str) -> List[Dict[str, Any]]:
        pass