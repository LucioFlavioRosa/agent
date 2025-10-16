from services.cache_service import CacheService
from services.workflow_registry_service import WorkflowRegistryService
from services.job_logging_service import JobLoggingService
from services.pull_request_extractor_service import PullRequestExtractorService
from services.api_service_factory import ApiServiceFactory
from services.analysis_name_service import AnalysisNameService, AnalysisNameCache
from services.job_data_service import JobDataService
from services.job_validation_service import JobValidationService
from services.repository_normalizer_service import RepositoryNormalizerService
from services.response_builder_service import ResponseBuilderService
from services.job_manager import JobManager
from services.blob_storage_service import BlobStorageService
from services.workflow_orchestrator import WorkflowOrchestrator
from services.job_manager import JobManager
from services.blob_storage_service import BlobStorageService
from services.workflow_orchestrator import WorkflowOrchestrator
from tools.job_store import RedisJobStore

class DependencyContainer:
    _cache_service_instance = None

    def __init__(self):
       
        self._cache_service = CacheService()
        self._analysis_name_service = AnalysisNameService(cache=self._cache_service)
        self._workflow_registry_service = WorkflowRegistryService()
        self._job_logging_service = JobLoggingService()
        self._pull_request_extractor_service = PullRequestExtractorService()
        self._api_service_factory = ApiServiceFactory(self._pull_request_extractor_service, self._job_logging_service)
        self._job_data_service = JobDataService()
        self._job_validation_service = JobValidationService()
        self._repository_normalizer_service = RepositoryNormalizerService()
        self._response_builder_service = ResponseBuilderService(pr_extractor=self._pull_request_extractor_service, logging_service=self._job_logging_service)
        self._job_store = RedisJobStore()
        self._job_manager = JobManager(job_store=self._job_store)
        self._analysis_name_cache = AnalysisNameCache(job_store=self._job_store)
        self._analysis_name_service = AnalysisNameService(cache=self._analysis_name_cache)
        self._blob_storage_service = BlobStorageService()

    def get_workflow_registry_service(self):
        return self._workflow_registry_service

    def get_job_logging_service(self):
        return self._job_logging_service

    def get_pull_request_extractor_service(self):
        return self._pull_request_extractor_service

    def get_api_service_factory(self):
        return self._api_service_factory

    def get_analysis_name_service(self):
        return self._analysis_name_service

    def get_job_data_service(self):
        return self._job_data_service

    def get_job_validation_service(self):
        return self._job_validation_service

    def get_repository_normalizer_service(self):
        return self._repository_normalizer_service

    def get_response_builder_service(self):
        return self._response_builder_service

    def get_job_manager(self):
        return self._job_manager

    def get_job_store(self):
        return self._job_store

    def get_blob_storage(self):
        return self._blob_storage_service

    def get_cache_service(self):
        if DependencyContainer._cache_service_instance is None:
            DependencyContainer._cache_service_instance = CacheService()
        return DependencyContainer._cache_service_instance

    def get_workflow_orchestrator(self):
        return WorkflowOrchestrator(
            job_manager=self.get_job_manager(),
            blob_storage=self.get_blob_storage(),
            workflow_registry=self.get_workflow_registry_service(),
            cache_service=self.get_cache_service()
        )
