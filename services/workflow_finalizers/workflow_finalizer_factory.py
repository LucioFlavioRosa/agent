from services.workflow_finalizers.commit_workflow_finalizer import CommitWorkflowFinalizer
from services.workflow_finalizers.azure_devops_workflow_finalizer import AzureDevOpsWorkflowFinalizer
from services.workflow_finalizers.epic_creation_workflow_finalizer import EpicCreationWorkflowFinalizer

class WorkflowFinalizerFactory:
    def __init__(self, data_formatter, job_handler, commit_handler, azure_devops_service, dotnet_build_service):
        self.data_formatter = data_formatter
        self.job_handler = job_handler
        self.commit_handler = commit_handler
        self.azure_devops_service = azure_devops_service
        self.dotnet_build_service = dotnet_build_service

    def get_finalizer(self, workflow_mode):
        if workflow_mode == 'epic_task_creation':
            return EpicCreationWorkflowFinalizer(self.azure_devops_service, self.job_handler)
        elif workflow_mode == 'azure_devops':
            return AzureDevOpsWorkflowFinalizer(self.azure_devops_service, self.job_handler)
        else:
            return CommitWorkflowFinalizer(self.data_formatter, self.job_handler, self.commit_handler, self.dotnet_build_service)
