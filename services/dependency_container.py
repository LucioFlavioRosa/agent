from tools.job_store import RedisJobStore
from services.workflow_orchestrator import WorkflowOrchestrator
from services.job_manager import JobManager
from services.blob_storage_service import BlobStorageService
from services.analysis_name_service import AnalysisNameService, AnalysisNameCache
from services.workflow_registry_service import WorkflowRegistryService
from services.report_manager import ReportManager
from services.commit_manager import CommitManager
from services.approval_handler import ApprovalHandler
from tools.rag_retriever import AzureAISearchRAGRetriever


class DependencyContainer:
    def __init__(self):
        self._job_store = None
        self._job_manager = None
        self._blob_storage = None
        self._workflow_registry_service = None
        self._workflow_orchestrator = None
        self._analysis_name_service = None
        self._report_manager = None
        self._commit_manager = None
        self._approval_handler = None
        self._rag_retriever = None
        self._blob_storage_service = None
        self._workflow_registry_service = None
        self._workflow_registry = None

    def get_report_manager(self):
        if self._report_manager is None:
            self._report_manager = ReportManager(
            blob_storage_service=self.get_blob_storage_service(),
            job_manager=self.get_job_manager() 
        )
        return self._report_manager

    def get_commit_manager(self):
        if self._commit_manager is None:
            conexao_geral = ConexaoGeral.create_with_defaults()
            self._commit_manager = CommitManager(conexao_geral)
        return self._commit_manager

    def get_approval_handler(self):
        if self._approval_handler is None:
            self._approval_handler = ApprovalHandler(self.get_job_manager(), self.get_report_manager())
        return self._approval_handler
    
    def get_rag_retriever(self):
        if self._rag_retriever is None:
            self._rag_retriever = AzureAISearchRAGRetriever()
        return self._rag_retriever
    
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

    def get_blob_storage_service(self):
        if self._blob_storage_service is None:
            self._blob_storage_service = BlobStorageService()
        return self._blob_storage_service
        
    def get_workflow_registry(self) -> dict:
        if self._workflow_registry is None:
            registry_service = self.get_workflow_registry_service()
            self._workflow_registry = registry_service.registry
            
        return self._workflow_registry
    
    def get_workflow_orchestrator(self):
        if self._workflow_orchestrator is None:
            self._workflow_orchestrator = WorkflowOrchestrator(
                registry_service = self.get_workflow_registry_service(),
                job_manager=self.get_job_manager(),
                blob_storage=self.get_blob_storage_service(),
                workflow_registry=self.get_workflow_registry(),
                report_manager=self.get_report_manager(),
                commit_manager=self.get_commit_manager(),
                approval_handler=self.get_approval_handler(),
                rag_retriever=self.get_rag_retriever()
            )
        return self._workflow_orchestrator
    
    def get_analysis_name_service(self) -> AnalysisNameService:
        if self._analysis_name_service is None:
            cache = AnalysisNameCache(self.get_job_store())
            self._analysis_name_service = AnalysisNameService(cache)
        return self._analysis_name_service
