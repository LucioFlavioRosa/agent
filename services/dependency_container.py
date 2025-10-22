from tools.job_store import RedisJobStore
from services.workflow_orchestrator import WorkflowOrchestrator
from services.job_manager import JobManager
from services.blob_storage_service import BlobStorageService
from services.analysis_name_service import AnalysisNameService, AnalysisNameCache
from services.workflow_registry_service import WorkflowRegistryService
from services.job_handler import JobHandler
from services.report_handler import ReportHandler
from services.commit_handler import CommitHandler
from services.data_formatter import DataFormatter
from tools.rag_retriever import AzureAISearchRAGRetriever
from tools.preenchimento import ChangesetFiller
from services.redis_cache_service import RedisCacheService
from tools.azure_secret_manager import AzureSecretManager

class DependencyContainer:
    def __init__(self):
        self._job_store = None
        self._job_manager = None
        self._blob_storage = None
        self._workflow_registry_service = None
        self._workflow_orchestrator = None
        self._analysis_name_service = None
        self._job_handler = None
        self._report_handler = None
        self._commit_handler = None
        self._data_formatter = None
        self._rag_retriever = None
        self._changeset_filler = None
        self._redis_cache_service = None
        self._secret_manager = None
    
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
    
    def get_rag_retriever(self) -> AzureAISearchRAGRetriever:
        if self._rag_retriever is None:
            self._rag_retriever = AzureAISearchRAGRetriever()
        return self._rag_retriever
    
    def get_changeset_filler(self) -> ChangesetFiller:
        if self._changeset_filler is None:
            self._changeset_filler = ChangesetFiller()
        return self._changeset_filler
    
    def get_job_handler(self) -> JobHandler:
        if self._job_handler is None:
            self._job_handler = JobHandler(self.get_job_manager())
        return self._job_handler
    
    def get_report_handler(self) -> ReportHandler:
        if self._report_handler is None:
            self._report_handler = ReportHandler(self.get_blob_storage())
        return self._report_handler
    
    def get_commit_handler(self) -> CommitHandler:
        if self._commit_handler is None:
            self._commit_handler = CommitHandler()
        return self._commit_handler
    
    def get_data_formatter(self) -> DataFormatter:
        if self._data_formatter is None:
            self._data_formatter = DataFormatter(self.get_changeset_filler())
        return self._data_formatter

    def get_secret_manager(self) -> AzureSecretManager:
        if self._secret_manager is None:
             self._secret_manager = AzureSecretManager()
        return self._secret_manager
    
    def get_redis_cache_service(self) -> RedisCacheService:
        if self._redis_cache_service is None:
            # Pega a instância única do job_store e a injeta no RedisCacheService
            job_store_instance = self.get_job_store()
            self._redis_cache_service = RedisCacheService(job_store=job_store_instance)
        return self._redis_cache_service
    
    def get_workflow_orchestrator(self) -> WorkflowOrchestrator:
        if self._workflow_orchestrator is None:
            workflow_registry = self.get_workflow_registry_service().get_workflow_registry()
            
            self._workflow_orchestrator = WorkflowOrchestrator(
                job_manager=self.get_job_manager(), 
                blob_storage=self.get_blob_storage(), 
                workflow_registry=workflow_registry,
                rag_retriever=self.get_rag_retriever(),
                job_handler=self.get_job_handler(),
                report_handler=self.get_report_handler(),
                commit_handler=self.get_commit_handler(),
                data_formatter=self.get_data_formatter(),
                secret_manager=self.get_secret_manager(),
                cache_service=self.get_redis_cache_service()
            )
        return self._workflow_orchestrator
    
    def get_analysis_name_service(self) -> AnalysisNameService:
        if self._analysis_name_service is None:
            cache = AnalysisNameCache(self.get_job_store())
            self._analysis_name_service = AnalysisNameService(cache)
        return self._analysis_name_service
