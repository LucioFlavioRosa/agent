from services.dependency_container import DependencyContainer
from azure_mcp.services.azure_workflow_registry_service import AzureWorkflowRegistryService
from services.azure_board_service import AzureBoardService
from services.task_discussion_updater_service import TaskDiscussionUpdaterService
from tools.azure_secret_manager import AzureSecretManager
from services.job_store import JobStore
from services.blob_storage_service import BlobStorageService
from services.workflow_orchestrator import WorkflowOrchestrator

class AzureDependencyContainer(DependencyContainer):
    def __init__(self):
        # Instancia apenas os serviços necessários para workflows Azure
        self._azure_workflow_registry_service = AzureWorkflowRegistryService()
        self._job_store = JobStore()
        self._blob_storage_service = BlobStorageService()
        self._azure_secret_manager = AzureSecretManager()
        self._azure_board_service = AzureBoardService(
            organization=None,
            project=None,
            secret_manager=self._azure_secret_manager
        )
        self._task_discussion_updater_service = TaskDiscussionUpdaterService()
        self._workflow_orchestrator = WorkflowOrchestrator(
            job_manager=self._job_store,
            blob_storage=self._blob_storage_service,
            workflow_registry=self._azure_workflow_registry_service.get_workflow_registry(),
            dependency_container=self,
            azure_board_service=self._azure_board_service
        )

    def get_workflow_registry_service(self):
        return self._azure_workflow_registry_service

    def get_job_store(self):
        return self._job_store

    def get_blob_storage_service(self):
        return self._blob_storage_service

    def get_secret_manager(self):
        return self._azure_secret_manager

    def get_azure_board_service(self):
        return self._azure_board_service

    def get_task_discussion_updater_service(self):
        return self._task_discussion_updater_service

    def get_workflow_orchestrator(self):
        return self._workflow_orchestrator
