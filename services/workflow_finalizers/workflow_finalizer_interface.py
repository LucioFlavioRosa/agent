from abc import ABC, abstractmethod

class IWorkflowFinalizer(ABC):
    @abstractmethod
    def finalize(self, job_id, job_info, workflow, final_result, repository_type, repo_name):
        pass
