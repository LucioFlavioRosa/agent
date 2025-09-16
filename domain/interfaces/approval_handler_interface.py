from abc import ABC, abstractmethod
from typing import Dict, Any

class IApprovalHandler(ABC):
    @abstractmethod
    def handle_approval_step(self, job_id: str, job_info: Dict[str, Any], step_index: int, step_result: Dict[str, Any]) -> None:
        pass