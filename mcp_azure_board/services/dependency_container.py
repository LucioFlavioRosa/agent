from mcp_azure_board.tools.job_store import JobStore
from services.blob_storage_service import BlobStorageService
from services.workflow_registry_service import WorkflowRegistryService
from services.workflow_orchestrator import WorkflowOrchestrator
from services.azure_board_service import AzureBoardService
from services.analysis_name_service import AnalysisNameService
from tools.azure_secret_manager import AzureSecretManager

class DependencyContainer:
    """
    Container de dependências simplificado para MCP Azure Board.
    Gerencia apenas os serviços essenciais para operações de board Azure.
    """
    def __init__(self):
        self._job_store = None
        self._blob_storage_service = None
        self._workflow_registry_service = None
        self._workflow_orchestrator = None
        self._azure_board_service = None
        self._analysis_name_service = None
        self._azure_secret_manager = None

    def get_job_store(self):
        if self._job_store is None:
            self._job_store = JobStore()
        return self._job_store

    def get_blob_storage_service(self):
        if self._blob_storage_service is None:
            self._blob_storage_service = BlobStorageService()
        return self._blob_storage_service

    def get_workflow_registry_service(self):
        if self._workflow_registry_service is None:
            self._workflow_registry_service = WorkflowRegistryService()
        return self._workflow_registry_service

    def get_workflow_orchestrator(self):
        if self._workflow_orchestrator is None:
            self._workflow_orchestrator = WorkflowOrchestrator(
                job_manager=self.get_job_store(),
                blob_storage=self.get_blob_storage_service(),
                workflow_registry=self.get_workflow_registry_service().get_workflow_registry(),
                azure_board_service=self.get_azure_board_service(),
                dependency_container=self
            )
        return self._workflow_orchestrator

    def get_azure_board_service(self):
        if self._azure_board_service is None:
            self._azure_board_service = AzureBoardService(
                organization=None, project=None, secret_manager=self.get_azure_secret_manager()
            )
        return self._azure_board_service

    def get_analysis_name_service(self):
        if self._analysis_name_service is None:
            self._analysis_name_service = AnalysisNameService()
        return self._analysis_name_service

    def get_azure_secret_manager(self):
        if self._azure_secret_manager is None:
            self._azure_secret_manager = AzureSecretManager()
        return self._azure_secret_manager
