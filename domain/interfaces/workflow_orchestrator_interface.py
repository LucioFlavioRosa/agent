from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class IWorkflowOrchestrator(ABC):
    @abstractmethod
    def execute_workflow(self, job_id: str, start_from_step: int = 0) -> None:
        pass
    
    @abstractmethod
    def handle_approval_step(self, job_id: str, step_index: int, step_result: Dict[str, Any]) -> None:
        pass