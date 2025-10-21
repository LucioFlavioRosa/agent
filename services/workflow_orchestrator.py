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
    def __init__(
        self,
        job_manager: IJobManager,
        blob_storage: IBlobStorageService,
        workflow_registry: Dict[str, Any],
        rag_retriever=None,
        job_handler=None,
        report_handler: ReportHandler = None,
        commit_handler=None,
        data_formatter: DataFormatter = None,
        secret_manager: Optional[Any] = None,
        cache_service=None,
        dependency_container=None,
        epic_and_task_creation_service=None,
        commit_and_build_service=None,
        llm_provider_factory: Optional[ILLMProviderFactory] = None,
        repository_provider_factory: Optional[IRepositoryProviderFactory] = None,
        repo_reader_factory=None,
        workflow_execution_strategy_factory=None
    ):
        self.workflow_registry = workflow_registry
        self.rag_retriever = self._init_rag_retriever(rag_retriever)
        self.job_handler = job_handler
        self.report_handler = self._init_report_handler(report_handler, blob_storage)
        self.commit_handler = commit_handler
        self.data_formatter = self._init_data_formatter(data_formatter)
        self.secret_manager = self._init_secret_manager(secret_manager)
        self.cache_service = self._init_cache_service(cache_service, dependency_container)
        self.dependency_container = dependency_container
        self.epic_and_task_creation_service = epic_and_task_creation_service
        self.commit_and_build_service = commit_and_build_service
        self.llm_provider_factory = llm_provider_factory
        self.repository_provider_factory = repository_provider_factory
        self.repo_reader_factory = repo_reader_factory or self._default_repo_reader_factory
        self.workflow_execution_strategy_factory = workflow_execution_strategy_factory or self._default_workflow_execution_strategy_factory

    def _init_rag_retriever(self, rag_retriever):
        return rag_retriever if rag_retriever is not None else AzureAISearchRAGRetriever()

    def _init_report_handler(self, report_handler, blob_storage):
        return report_handler if report_handler is not None else ReportHandler(blob_storage)

    def _init_data_formatter(self, data_formatter):
        return data_formatter if data_formatter is not None else DataFormatter()

    def _init_secret_manager(self, secret_manager):
        return secret_manager if secret_manager is not None else AzureSecretManager()

    def _init_cache_service(self, cache_service, dependency_container):
        if cache_service is not None:
            return cache_service
        if dependency_container is not None and hasattr(dependency_container, 'get_redis_cache_service'):
            return dependency_container.get_redis_cache_service()
        return None

    def _default_repo_reader_factory(self, repository_provider, cache_service):
        return ReaderGeral(repository_provider=repository_provider, cache_service=cache_service)

    def _default_workflow_execution_strategy_factory(self, job_info):
        return WorkflowExecutionStrategyFactory.create_strategy(
            job_info=job_info,
            job_handler=self.job_handler,
            report_handler=self.report_handler,
            epic_and_task_creation_service=self.epic_and_task_creation_service,
            commit_and_build_service=self.commit_and_build_service,
            incremental_step_executor_service=self.dependency_container.incremental_step_executor_service if self.dependency_container and hasattr(self.dependency_container, 'incremental_step_executor_service') else None,
            llm_provider_factory=self.llm_provider_factory
        )

    def execute_workflow(self, job_id: str, start_from_step: int = 0) -> None:
        job_info = self.job_handler.get_job_info(job_id)
        workflow = self.workflow_registry.get(job_info['data']['original_analysis_type'])
        if not workflow:
            raise ValueError("Workflow não encontrado.")
        repository_type = job_info['data']['repository_type']
        repo_name = job_info['data']['repo_name']
        repository_provider = self.repository_provider_factory.get_provider(repository_type)
        repo_reader = self.repo_reader_factory(repository_provider, self.cache_service)
        strategy = self.workflow_execution_strategy_factory(job_info)
        strategy.execute(job_id, job_info, workflow, start_from_step, repo_reader)

    def handle_approval_step(self, job_id: str, job_info: Dict[str, Any], step_index: int, step_result: Dict[str, Any]) -> None:
        print(f"[{job_id}] Etapa {step_index} requer aprovação.")
        report_text = self.report_handler.extract_report_text(step_result)
        if not report_text:
            print(f"[{job_id}] AVISO: Tentando pausar para aprovação sem relatório no step_result.")
            report_text = job_info['data'].get('analysis_report', '')
            if not report_text:
                raise ValueError(f"[{job_id}] ERRO CRÍTICO: Pausa para aprovação sem relatório disponível.")
        if not job_info['data'].get('report_blob_url'):
            print(f"[{job_id}] Salvando relatório antes de pausar para aprovação...")
            self._save_generated_report(job_id, job_info, step_result, step_index)
            if not job_info['data'].get('report_blob_url'):
                raise ValueError(f"[{job_id}] ERRO CRÍTICO: Falha ao salvar relatório antes de pausar.")
        job_info['data']['analysis_report'] = report_text
        job_info['status'] = 'pending_approval'
        self.job_handler.set_paused_step(job_info, step_index)
        self.job_handler.update_job(job_id, job_info)
        print(f"[{job_id}] Workflow pausado na etapa {step_index} aguardando aprovação.")

    def _save_generated_report(self, job_id, job_info, step_result, step_index):
        report_text = self.report_handler.extract_report_text(step_result)
        if not report_text:
            report_text = job_info['data'].get('analysis_report', '')
        if not report_text:
            raise ValueError(f"[{job_id}] ERRO: Nenhum relatório disponível para salvar no Blob Storage.")
        url = self.report_handler.save_report_to_blob(job_id, job_info, report_text, report_generated_by_agent=True)
        job_info['data']['report_blob_url'] = url
