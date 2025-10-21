import json
from typing import Dict, Any, Optional
from domain.interfaces.workflow_orchestrator_interface import IWorkflowOrchestrator
from domain.interfaces.job_manager_interface import IJobManager
from domain.interfaces.blob_storage_interface import IBlobStorageService
from services.factories.llm_provider_factory import LLMProviderFactory
from services.job_handler import JobHandler
from services.report_handler import ReportHandler
from services.commit_handler import CommitHandler
from services.data_formatter import DataFormatter
from services.step_strategies.step_strategy_factory import StepStrategyFactory
from tools.rag_retriever import AzureAISearchRAGRetriever
from tools.readers.reader_geral import ReaderGeral
from models import JobFields
from services.incremental_step_executor_service import IncrementalStepExecutorService
from services.dotnet_build_service import DotNetBuildService
from tools.azure_secret_manager import AzureSecretManager
from services.epico_parser_service import EpicoParserService
from services.tarefa_parser_service import TarefaParserService
import re

class WorkflowOrchestrator(IWorkflowOrchestrator):
    def __init__(self, job_manager: IJobManager, blob_storage: IBlobStorageService,
                 workflow_registry: Dict[str, Any], rag_retriever=None,
                 job_handler: JobHandler = None, report_handler: ReportHandler = None,
                 commit_handler: CommitHandler = None, data_formatter: DataFormatter = None,
                 secret_manager: Optional[Any] = None, cache_service=None, dependency_container=None,
                 epic_and_task_creation_service=None, llm_provider_factory=None, repository_provider_factory=None):
        self.workflow_registry = workflow_registry
        self.rag_retriever = rag_retriever or AzureAISearchRAGRetriever()
        self.job_handler = job_handler or JobHandler(job_manager)
        self.report_handler = report_handler or ReportHandler(blob_storage)
        self.commit_handler = commit_handler or CommitHandler()
        self.data_formatter = data_formatter or DataFormatter()
        self.secret_manager = secret_manager or AzureSecretManager()
        self.cache_service = cache_service
        self.dependency_container = dependency_container
        self.epic_and_task_creation_service = epic_and_task_creation_service
        self.llm_provider_factory = llm_provider_factory or LLMProviderFactory()
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
        executar_incremental = job_info['data'].get(JobFields.EXECUTAR_STEPS_INCREMENTALMENTE, False)
        if executar_incremental:
            batch_results = IncrementalStepExecutorService.execute_incremental_workflow(job_id, job_info, workflow, start_from_step, repo_reader)
            final_result = IncrementalStepExecutorService.merge_all_batches(batch_results)
            dados_finais_formatados = self.data_formatter.format_incremental_result_for_commit(final_result)
            self.job_handler.update_job_status(job_id, 'committing_to_github')
            self.commit_handler.execute_commits(job_id, job_info, dados_finais_formatados, repository_type, repo_name)
            self.job_handler.update_job_status(job_id, 'completed')
            self.job_handler.update_job(job_id, job_info)
            return
        if job_info['data']['original_analysis_type'] == 'geracao_epicos_a_partir_de_reuniao':
            analysis_report = job_info['data'].get('analysis_report')
            organization_url = None
            project_name = None
            if repository_type == 'azure':
                parts = repo_name.split('/')
                if len(parts) >= 2:
                    organization_url = f"https://dev.azure.com/{parts[0]}"
                    project_name = job_info['data'].get('azure_project_name') or parts[1]
            if not organization_url:
                organization_url = job_info['data'].get('organization_url')
            if not project_name:
                project_name = job_info['data'].get('azure_project_name')
            if not organization_url or not project_name:
                raise ValueError("organization_url e project_name são obrigatórios para criar cards no Azure Boards.")
            result = self.epic_and_task_creation_service.create_epics_and_tasks_from_report(
                job_id, job_info, analysis_report, organization_url, project_name
            )
            job_info['data']['cards_criados'] = result['cards_criados']
            job_info['data']['tarefas_criadas'] = result['tarefas_criadas']
            job_info['data']['tarefas_creation_errors'] = result['tarefas_creation_errors']
            job_info['data']['tarefas_parsing_errors'] = result['tarefas_parsing_errors']
            self.job_handler.update_job_status(job_id, 'completed')
            self.job_handler.update_job(job_id, job_info)
            return
        previous_step_result = self.job_handler.get_step_result(job_info, start_from_step)
        steps_to_run = workflow.get('steps', [])[start_from_step:]
        for i, step in enumerate(steps_to_run):
            current_step_index = start_from_step + i
            self.job_handler.update_job_status(job_id, step['status_update'])
            model_para_etapa = step.get('model_name', job_info.get('data', {}).get('model_name'))
            llm_provider = self.llm_provider_factory.create_provider(model_para_etapa, self.rag_retriever)
            agent_params = step.get('params', {}).copy() if step.get('params') else {}
            agent_params['job_id'] = job_id
            strategy = StepStrategyFactory.create_strategy(step, self.job_handler, self.report_handler)
            step_result = strategy.execute_step(
                job_id, job_info, step, current_step_index,
                previous_step_result, repo_reader, llm_provider, agent_params
            )
            self.job_handler.save_step_result(job_info, current_step_index, step_result)
            previous_step_result = step_result
            if strategy.should_pause_for_approval(job_info, step):
                report_text = self.report_handler.extract_report_text(step_result)
                if not report_text or len(report_text.strip()) == 0:
                    report_text = job_info['data'].get('analysis_report', '')
                    if not report_text or len(report_text.strip()) == 0:
                        return
                job_info['data']['analysis_report'] = report_text
                url = self.report_handler.save_report_to_blob(job_id, job_info, report_text, report_generated_by_agent=True)
                if not url:
                    raise ValueError(f"[{job_id}] ERRO CRÍTICO: Relatório não foi salvo no Blob Storage")
                job_info['data']['report_blob_url'] = url
                self.job_handler.update_job(job_id, job_info)
                self.job_handler.set_paused_step(job_info, current_step_index)
                self.job_handler.update_job(job_id, job_info)
                return
            if strategy.should_finalize_workflow(job_info, current_step_index):
                self.job_handler.update_job_status(job_id, 'completed')
                self.job_handler.update_job(job_id, job_info)
                return
        final_result = previous_step_result
        self.job_handler.update_job_status(job_id, 'committing_to_github')
        self.commit_handler.execute_commits(job_id, job_info, final_result, repository_type, repo_name)
        self.job_handler.update_job_status(job_id, 'completed')
        self.job_handler.update_job(job_id, job_info)
