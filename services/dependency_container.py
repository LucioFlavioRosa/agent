# --- Importações necessárias ---
from tools.job_store import RedisJobStore
from services.workflow_orchestrator import WorkflowOrchestrator
from services.job_manager import JobManager
from services.blob_storage_service import BlobStorageService
from services.analysis_name_service import AnalysisNameService, AnalysisNameCache
from services.workflow_registry_service import WorkflowRegistryService
from tools.rag_retriever import AzureAISearchRAGRetriever
from tools.preenchimento import ChangesetFiller
from tools.azure_secret_manager import AzureSecretManager
# Importe a nova FÁBRICA
from tools.repository_provider_factory import RepositoryProviderFactory

class DependencyContainer:
    """
    Container para gerenciar a criação e o ciclo de vida dos serviços (Injeção de Dependência).
    """
    def __init__(self):
        # Cache para os serviços singleton
        self._job_store = None
        self._job_manager = None
        self._blob_storage_service = None
        self._workflow_registry_service = None
        self._workflow_orchestrator = None
        self._analysis_name_service = None
        self._rag_retriever = None
        self._changeset_filler = None
        self._secret_manager = None
        self._repository_provider_factory = None # Novo: cache para a fábrica

    # --- Getters para Serviços Singleton ---

    def get_job_store(self) -> RedisJobStore:
        if self._job_store is None:
            self._job_store = RedisJobStore()
        return self._job_store

    def get_job_manager(self) -> JobManager:
        if self._job_manager is None:
            self._job_manager = JobManager(self.get_job_store())
        return self._job_manager

    def get_blob_storage_service(self) -> BlobStorageService:
        if self._blob_storage_service is None:
            self._blob_storage_service = BlobStorageService()
        return self._blob_storage_service

    def get_workflow_registry_service(self) -> WorkflowRegistryService:
        if self._workflow_registry_service is None:
            self._workflow_registry_service = WorkflowRegistryService()
        return self._workflow_registry_service
    
    def get_secret_manager(self) -> AzureSecretManager:
        if self._secret_manager is None:
            self._secret_manager = AzureSecretManager()
        return self._secret_manager

    def get_analysis_name_service(self) -> AnalysisNameService:
        if self._analysis_name_service is None:
            cache = AnalysisNameCache(self.get_job_store())
            self._analysis_name_service = AnalysisNameService(cache)
        return self._analysis_name_service

    def get_rag_retriever(self) -> AzureAISearchRAGRetriever:
        if self._rag_retriever is None:
            self._rag_retriever = AzureAISearchRAGRetriever()
        return self._rag_retriever

    def get_changeset_filler(self) -> ChangesetFiller:
        if self._changeset_filler is None:
            self._changeset_filler = ChangesetFiller()
        return self._changeset_filler

    # --- NOVO: Getter para a FÁBRICA ---
    def get_repository_provider_factory(self) -> RepositoryProviderFactory:
        if self._repository_provider_factory is None:
            # A fábrica precisa do secret manager para buscar os tokens dinâmicos
            self._repository_provider_factory = RepositoryProviderFactory(
                secret_manager=self.get_secret_manager()
            )
        return self._repository_provider_factory

    # --- ATUALIZADO: get_workflow_orchestrator ---
    def get_workflow_orchestrator(self) -> WorkflowOrchestrator:
        if self._workflow_orchestrator is None:
            # Pega o dicionário de workflows a partir do serviço
            workflow_registry_dict = self.get_workflow_registry_service().registry

            # Cria o orquestrador injetando apenas as dependências singleton/fábricas
            self._workflow_orchestrator = WorkflowOrchestrator(
                job_manager=self.get_job_manager(),
                blob_storage=self.get_blob_storage_service(),
                workflow_registry=workflow_registry_dict,
                rag_retriever=self.get_rag_retriever(),
                changeset_filler=self.get_changeset_filler(),
                # INJETA A FÁBRICA, e não um provider/reader específico
                provider_factory=self.get_repository_provider_factory()
            )
        return self._workflow_orchestrator
