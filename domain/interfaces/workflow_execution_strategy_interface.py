from abc import ABC, abstractmethod
from typing import Dict, Any

class IWorkflowExecutionStrategy(ABC):
    @abstractmethod
    def execute(
        self,
        job_id: str,
        job_info: Dict[str, Any],
        workflow: Dict[str, Any],
        start_from_step: int,
        repo_reader: Any
    ) -> None:
        pass
