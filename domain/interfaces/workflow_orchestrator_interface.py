from abc import ABC, abstractmethod

class IWorkflowOrchestrator(ABC):
    @abstractmethod
    def execute_workflow(self, job_id: str, start_from_step: int = 0) -> None:
        pass
