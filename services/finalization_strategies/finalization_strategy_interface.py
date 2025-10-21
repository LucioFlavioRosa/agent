from abc import ABC, abstractmethod
from typing import Any, Dict

class IFinalizationStrategy(ABC):
    @abstractmethod
    def finalize(self, job_id: str, job_info: Dict[str, Any], final_result: Dict[str, Any], repository_type: str, repo_name: str):
        pass
