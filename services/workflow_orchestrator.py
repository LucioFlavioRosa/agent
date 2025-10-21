from typing import Dict, Any, Optional
from domain.interfaces.workflow_orchestrator_interface import IWorkflowOrchestrator
from domain.interfaces.job_manager_interface import IJobManager
from domain.interfaces.blob_storage_interface import IBlobStorageService
from domain.interfaces.llm_provider_factory_interface import ILLMProviderFactory
from domain.interfaces.repository_provider_factory_interface import IRepositoryProviderFactory
from services.report_handler import ReportHandler
from services.data_formatter import DataFormatter
from services.step_strategies.step_strategy_factory import StepStrategyFactory
from tools.rag_retriever import AzureAISearchRAGRetriever
from tools.readers.reader_geral import ReaderGeral
from models import JobFields
from tools.azure_secret_manager import AzureSecretManager
from services.workflow_execution_strategies.workflow_execution_strategy_factory import WorkflowExecutionStrategyFactory

class WorkflowOrchestrator(IWorkflowOrchestrator):
    def __init__(self, job_manager: IJobManager, blob_storage: IBlobStorageService,
                 workflow_registry: Dict[str, Any], rag_retriever=None,
                 job_handler=None, report_handler: ReportHandler = None,
                 commit_handler=None, data_formatter: DataFormatter = None,
                 secret_manager: Optional[Any] = None, cache_service=None, dependency_container=None,
                 epic_and_task_creation_service=None, commit_and_build_service=None,
                 llm_provider_factory: Optional[ILLMProviderFactory] = None,
                 repository_provider_factory: Optional[IRepositoryProviderFactory] = None):
        self.workflow_registry = workflow_registry
        self.rag_retriever = rag_retriever or AzureAISearchRAGRetriever()
        self.job_handler = job_handler
        self.report_handler = report_handler or ReportHandler(blob_storage)
        self.commit_handler = commit_handler
        self.data_formatter = data_formatter or DataFormatter()
        self.secret_manager = secret_manager or AzureSecretManager()
        self.cache_service = cache_service
        self.dependency_container = dependency_container
        self.epic_and_task_creation_service = epic_and_task_creation_service
        self.commit_and_build_service = commit_and_build_service
        self.llm_provider_factory = llm_provider_factory
        self.repository_provider_factory = repository_provider_factory

    def execute_workflow(self, job_id: str, start_from_step: int = 0) -> None:
        job_info = self.job_handler.get_job_info(job_id)
        workflow = self.workflow_registry.get(job_info['data']['original_analysis_type'])
        if not workflow:
            raise ValueError("Workflow não encontrado.")
        repository_type = job_info['data']['repository_type']
        repo_name = job_info['data']['repo_name']
        repository_provider = self.repository_provider_factory.get_provider(repository_type)
        cache_service = self.cache_service or (self.dependency_container.get_redis_cache_service() if self.dependency_container else None)
        repo_reader = ReaderGeral(repository_provider=repository_provider, cache_service=cache_service)
        strategy = WorkflowExecutionStrategyFactory.create_strategy(
            job_info=job_info,
            job_handler=self.job_handler,
            report_handler=self.report_handler,
            epic_and_task_creation_service=self.epic_and_task_creation_service,
            commit_and_build_service=self.commit_and_build_service,
            incremental_step_executor_service=self.dependency_container.incremental_step_executor_service if self.dependency_container and hasattr(self.dependency_container, 'incremental_step_executor_service') else None,
            llm_provider_factory=self.llm_provider_factory
        )
        strategy.execute(job_id, job_info, workflow, start_from_step, repo_reader)
