from services.workflow_finalizers.commit_workflow_finalizer import CommitWorkflowFinalizer
from services.workflow_finalizers.azure_devops_workflow_finalizer import AzureDevOpsWorkflowFinalizer
from services.workflow_finalizers.epic_creation_workflow_finalizer import EpicCreationWorkflowFinalizer

class WorkflowFinalizerFactory:
    def __init__(self, data_formatter, job_handler, commit_handler, azure_devops_service, dotnet_build_service=None):
        self.data_formatter = data_formatter
        self.job_handler = job_handler
        self.commit_handler = commit_handler
        self.azure_devops_service = azure_devops_service
        self.dotnet_build_service = dotnet_build_service

    def get_finalizer(self, workflow_mode):
        if workflow_mode == 'epic_task_creation':
            return EpicCreationWorkflowFinalizer(
                azure_devops_service=self.azure_devops_service,
                job_handler=self.job_handler
            )
        elif workflow_mode == 'code_generation' or workflow_mode is None:
            return CommitWorkflowFinalizer(
                data_formatter=self.data_formatter,
                job_handler=self.job_handler,
                commit_handler=self.commit_handler,
                dotnet_build_service=self.dotnet_build_service
            )
        elif workflow_mode == 'azure_devops':
            return AzureDevOpsWorkflowFinalizer(
                azure_devops_service=self.azure_devops_service,
                job_handler=self.job_handler
            )
        else:
            raise ValueError(f"Workflow mode '{workflow_mode}' não suportado na factory de finalizadores.")
