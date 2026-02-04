from tools.job_store import RedisJobStore
from services.workflow_orchestrator import WorkflowOrchestrator
from services.job_manager import JobManager
from services.blob_storage_service import BlobStorageService
from services.workflow_registry_service import WorkflowRegistryService
from services.job_handler import JobHandler
from services.report_handler import ReportHandler
from services.redis_cache_service import RedisCacheService
from tools.azure_secret_manager import AzureSecretManager, VaultType
from services.mongodb_group_resolver_service import MongoDBGroupResolverService

class DependencyContainer:
    def __init__(self):
        self._job_store = None
        self._job_manager = None
        self._blob_storage_instances = {}
        self._workflow_registry_service = None
        self._workflow_orchestrator = None
        self._job_handler = None
        self._report_handler = None
        self._redis_cache_service = None
        self._secret_manager = None
        self._mongodb_group_resolver = None
    
    def get_job_store(self) -> RedisJobStore:
        if self._job_store is None:
            self._job_store = RedisJobStore()
        return self._job_store
    
    def get_job_manager(self) -> JobManager:
        if self._job_manager is None:
            self._job_manager = JobManager(self.get_job_store())
        return self._job_manager
    
    def get_mongodb_group_resolver(self) -> MongoDBGroupResolverService:
        if self._mongodb_group_resolver is None:
            self._mongodb_group_resolver = MongoDBGroupResolverService(
                secret_manager=AzureSecretManager(vault_type=VaultType.AZURE_INFRASTRUCTURE),
                vault_type=VaultType.AZURE_INFRASTRUCTURE
            )
        return self._mongodb_group_resolver
    
    def get_blob_storage(self, user_email: str = None) -> BlobStorageService:
        key = user_email or '__default__'
        if key not in self._blob_storage_instances:
            group_resolver = self.get_mongodb_group_resolver()
            secret_manager = AzureSecretManager(vault_type=VaultType.AZURE_INFRASTRUCTURE)
            self._blob_storage_instances[key] = BlobStorageService(
                user_email=user_email,
                group_resolver=group_resolver
            )
        return self._blob_storage_instances[key]
    
    def get_workflow_registry_service(self) -> WorkflowRegistryService:
        if self._workflow_registry_service is None:
            self._workflow_registry_service = WorkflowRegistryService()
        return self._workflow_registry_service
    
    def get_job_handler(self, user_email: str = None) -> JobHandler:
        if self._job_handler is None:
            self._job_handler = JobHandler(self.get_job_manager())
        return self._job_handler
    
    def get_report_handler(self, user_email: str = None) -> ReportHandler:
        if self._report_handler is None:
            blob_storage = self.get_blob_storage(user_email)
            group_resolver = self.get_mongodb_group_resolver()
            self._report_handler = ReportHandler(blob_storage, group_resolver=group_resolver)
        return self._report_handler
    
    def get_secret_manager(self) -> AzureSecretManager:
        if self._secret_manager is None:
             self._secret_manager = AzureSecretManager()
        return self._secret_manager
    
    def get_redis_cache_service(self) -> RedisCacheService:
        if self._redis_cache_service is None:
            job_store_instance = self.get_job_store()
            self._redis_cache_service = RedisCacheService(job_store=job_store_instance)
        return self._redis_cache_service
    
    def get_workflow_orchestrator(self, user_email: str = None) -> WorkflowOrchestrator:
        if self._workflow_orchestrator is None:
            workflow_registry = self.get_workflow_registry_service().get_workflow_registry()
            group_resolver = self.get_mongodb_group_resolver()
            self._workflow_orchestrator = WorkflowOrchestrator(
                job_manager=self.get_job_manager(), 
                blob_storage=self.get_blob_storage(user_email), 
                workflow_registry=workflow_registry,
                job_handler=self.get_job_handler(user_email),
                report_handler=self.get_report_handler(user_email),
                secret_manager=self.get_secret_manager(),
                cache_service=self.get_redis_cache_service(),
                dependency_container=self,
                group_resolver=group_resolver
            )
        return self._workflow_orchestrator
