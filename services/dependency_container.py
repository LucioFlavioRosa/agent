from tools.job_store import RedisJobStore
from services.workflow_orchestrator import WorkflowOrchestrator
from services.job_manager import JobManager
from services.blob_storage_service import BlobStorageService
from services.analysis_name_service import AnalysisNameService, AnalysisNameCache
from services.workflow_registry_service import WorkflowRegistryService

class DependencyContainer:
    def __init__(self):
        self._job_store = None
        self._job_manager = None
        self._blob_storage = None
        self._workflow_registry_service = None
        self._workflow_orchestrator = None
        self._analysis_name_service = None
    
    def get_job_store(self) -> RedisJobStore:
        if self._job_store is None:
            self._job_store = RedisJobStore()
        return self._job_store
    
    def get_job_manager(self) -> JobManager:
        if self._job_manager is None:
            self._job_manager = JobManager(self.get_job_store())
        return self._job_manager
    
    def get_blob_storage(self) -> BlobStorageService:
        if self._blob_storage is None:
            self._blob_storage = BlobStorageService()
        return self._blob_storage
    
    def get_workflow_registry_service(self) -> WorkflowRegistryService:
        if self._workflow_registry_service is None:
            self._workflow_registry_service = WorkflowRegistryService()
        return self._workflow_registry_service
    
    def get_workflow_orchestrator(self) -> WorkflowOrchestrator:
        if self._workflow_orchestrator is None:
            workflow_registry = self.get_workflow_registry_service().get_workflow_registry()
            self._workflow_orchestrator = WorkflowOrchestrator(
                self.get_job_manager(), 
                self.get_blob_storage(), 
                workflow_registry
            )
        return self._workflow_orchestrator
    
    def get_analysis_name_service(self) -> AnalysisNameService:
        if self._analysis_name_service is None:
            cache = AnalysisNameCache(self.get_job_store())
            self._analysis_name_service = AnalysisNameService(cache)
        return self._analysis_name_service