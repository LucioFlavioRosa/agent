from services.analysis_name_service import AnalysisNameService
from services.blob_storage_service import BlobStorageService
from services.workflow_registry_service import WorkflowRegistryService
from services.workflow_orchestrator import WorkflowOrchestrator
from services.azure_board_service import AzureBoardService
from tools.azure_secret_manager import AzureSecretManager
from tools.job_store import JobStore
from services.redis_cache_service import RedisCacheService

class DependencyContainer:
    def __init__(self):
        self._job_store = None
        self._blob_storage = None
        self._workflow_registry_service = None
        self._workflow_orchestrator = None
        self._analysis_name_service = None
        self._azure_board_service = None
        self._secret_manager = None
        self._cache_service = None

    def get_job_store(self):
        if self._job_store is None:
            self._job_store = JobStore()
        return self._job_store

    def get_blob_storage(self):
        if self._blob_storage is None:
            self._blob_storage = BlobStorageService()
        return self._blob_storage

    def get_workflow_registry_service(self):
        if self._workflow_registry_service is None:
            self._workflow_registry_service = WorkflowRegistryService()
        return self._workflow_registry_service

    def get_workflow_orchestrator(self):
        if self._workflow_orchestrator is None:
            self._workflow_orchestrator = WorkflowOrchestrator(
                job_manager=self.get_job_store(),
                blob_storage=self.get_blob_storage(),
                workflow_registry=self.get_workflow_registry_service().get_workflow_registry(),
                dependency_container=self,
                azure_board_service=self.get_azure_board_service(),
                cache_service=self.get_cache_service()
            )
        return self._workflow_orchestrator

    def get_analysis_name_service(self):
        if self._analysis_name_service is None:
            self._analysis_name_service = AnalysisNameService()
        return self._analysis_name_service

    def get_azure_board_service(self):
        if self._azure_board_service is None:
            self._azure_board_service = AzureBoardService()
        return self._azure_board_service

    def get_secret_manager(self):
        if self._secret_manager is None:
            self._secret_manager = AzureSecretManager()
        return self._secret_manager

    def get_cache_service(self):
        if self._cache_service is None:
            self._cache_service = RedisCacheService()
        return self._cache_service
