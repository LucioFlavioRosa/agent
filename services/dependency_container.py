import threading
from services.workflow_registry_service import WorkflowRegistryService
from services.api_service_factory import ApiServiceFactory
from services.pull_request_extractor_service import PullRequestExtractorService
from services.job_logging_service import JobLoggingService
from services.response_builder_service import FinalStatusResponse
from services.workflow_registry_loader import WorkflowRegistryLoader
from services.job_data_service import JobDataService
from services.job_validation_service import JobValidationService
from services.repository_normalizer_service import RepositoryNormalizerService
from services.job_handler import JobHandler
from services.report_handler import ReportHandler
from services.commit_handler import CommitHandler
from services.data_formatter import DataFormatter
from services.incremental_step_executor_service import IncrementalStepExecutorService
from services.redis_cache_service import RedisCacheService
from tools.azure_secret_manager import AzureSecretManager
from services.change_consolidator_service import ChangeConsolidatorService
from services.priority_mapper_service import PriorityMapperService
from services.step_dependency_analyzer import StepDependencyAnalyzer
from services.step_strategies.step_strategy_factory import StepStrategyFactory
from services.step_executors.step_executor_factory import StepExecutorFactory
from services.feature_parser_service import FeatureParserService
from services.task_parser_service import TaskParserService
from services.job_manager import JobManager
from services.blob_storage_service import BlobStorageService
from tools.job_store import JobStore

class DependencyContainer:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.workflow_registry_service = WorkflowRegistryService()
        self.api_service_factory = ApiServiceFactory(PullRequestExtractorService(), JobLoggingService())
        self.workflow_registry_loader = WorkflowRegistryLoader()
        self.job_data_service = JobDataService()
        self.job_validation_service = JobValidationService()
        self.repository_normalizer_service = RepositoryNormalizerService()
        self.job_handler = JobHandler(JobManager())
        self.report_handler = ReportHandler(BlobStorageService())
        self.commit_handler = CommitHandler()
        self.data_formatter = DataFormatter()
        self.incremental_step_executor_service = IncrementalStepExecutorService()
        self.redis_cache_service = RedisCacheService()
        self.azure_secret_manager = AzureSecretManager()
        self.change_consolidator_service = ChangeConsolidatorService()
        self.priority_mapper_service = PriorityMapperService()
        self.step_dependency_analyzer = StepDependencyAnalyzer()
        self.step_strategy_factory = StepStrategyFactory()
        self.step_executor_factory = StepExecutorFactory()
        self.feature_parser_service = FeatureParserService()
        self.task_parser_service = TaskParserService()
        self.job_manager = JobManager()
        self.blob_storage_service = BlobStorageService()
        self.job_store = JobStore()

    def get_workflow_registry_service(self):
        return self.workflow_registry_service

    def get_api_service_factory(self):
        return self.api_service_factory

    def get_workflow_registry_loader(self):
        return self.workflow_registry_loader

    def get_job_data_service(self):
        return self.job_data_service

    def get_job_validation_service(self):
        return self.job_validation_service

    def get_repository_normalizer_service(self):
        return self.repository_normalizer_service

    def get_job_handler(self):
        return self.job_handler

    def get_report_handler(self):
        return self.report_handler

    def get_commit_handler(self):
        return self.commit_handler

    def get_data_formatter(self):
        return self.data_formatter

    def get_incremental_step_executor_service(self):
        return self.incremental_step_executor_service

    def get_redis_cache_service(self):
        return self.redis_cache_service

    def get_azure_secret_manager(self):
        return self.azure_secret_manager

    def get_change_consolidator_service(self):
        return self.change_consolidator_service

    def get_priority_mapper_service(self):
        return self.priority_mapper_service

    def get_step_dependency_analyzer(self):
        return self.step_dependency_analyzer

    def get_step_strategy_factory(self):
        return self.step_strategy_factory

    def get_step_executor_factory(self):
        return self.step_executor_factory

    def get_feature_parser_service(self):
        return self.feature_parser_service

    def get_task_parser_service(self):
        return self.task_parser_service

    def get_job_manager(self):
        return self.job_manager

    def get_blob_storage(self):
        return self.blob_storage_service

    def get_job_store(self):
        return self.job_store
