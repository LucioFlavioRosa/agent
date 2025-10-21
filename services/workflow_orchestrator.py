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
from tools.repository_provider_factory import get_repository_provider_explicit
from models import JobFields
from services.incremental_step_executor_service import IncrementalStepExecutorService
from services.dotnet_build_service import DotNetBuildService
from tools.azure_secret_manager import AzureSecretManager
from services.epico_parser_service import EpicoParserService
from services.tarefa_parser_service import TarefaParserService
import re
from services.epic_and_task_creation_service import EpicAndTaskCreationService

class WorkflowOrchestrator(IWorkflowOrchestrator):
    def __init__(self, job_manager: IJobManager, blob_storage: IBlobStorageService, 
                 workflow_registry: Dict[str, Any], rag_retriever=None, 
                 job_handler: JobHandler = None, report_handler: ReportHandler = None,
                 commit_handler: CommitHandler = None, data_formatter: DataFormatter = None, secret_manager: Optional[Any] = None,
                 cache_service=None, dependency_container=None,
                 epic_and_task_creation_service: EpicAndTaskCreationService = None):
        self.workflow_registry = workflow_registry
        self.rag_retriever = rag_retriever or AzureAISearchRAGRetriever()
        self.job_handler = job_handler or JobHandler(job_manager)
        self.report_handler = report_handler or ReportHandler(blob_storage)
        self.commit_handler = commit_handler or CommitHandler()
        self.data_formatter = data_formatter or DataFormatter()
        self.secret_manager = secret_manager or AzureSecretManager()
        self.cache_service = cache_service
        self.dependency_container = dependency_container
        self.epic_and_task_creation_service = epic_and_task_creation_service or EpicAndTaskCreationService(
            dependency_container.get_azure_boards_service if dependency_container else None,
            EpicoParserService(),
            TarefaParserService()
        )

    def execute_workflow(self, job_id: str, start_from_step: int = 0) -> None:
        job_info = self.job_handler.get_job_info(job_id)
        workflow = self.workflow_registry.get(job_info['data']['original_analysis_type'])
        if not workflow:
            raise ValueError("Workflow não encontrado.")
        repository_type = job_info['data']['repository_type']
        repo_name = job_info['data']['repo_name']
        repository_provider = get_repository_provider_explicit(repository_type)
        cache_service = self.cache_service or (self.dependency_container.get_redis_cache_service() if self.dependency_container else None)
        repo_reader = ReaderGeral(repository_provider=repository_provider, cache_service=cache_service)
        executar_incremental = job_info['data'].get(JobFields.EXECUTAR_STEPS_INCREMENTALMENTE, False)
        if executar_incremental:
            IncrementalStepExecutorService.execute_incremental_workflow(
                job_id, job_info, workflow, repo_reader, self.job_handler, self.report_handler, start_from_step
            )
            return
        if job_info['data']['original_analysis_type'] == 'geracao_epicos_a_partir_de_reuniao':
            self._execute_epic_generation_workflow(job_id, job_info, workflow, repo_reader, start_from_step)
            return
        self._execute_default_workflow(job_id, job_info, workflow, repo_reader, start_from_step)

    def _execute_default_workflow(self, job_id, job_info, workflow, repo_reader, start_from_step):
        previous_step_result = self.job_handler.get_step_result(job_info, start_from_step)
        steps_to_run = workflow.get('steps', [])[start_from_step:]
        for i, step in enumerate(steps_to_run):
            current_step_index = start_from_step + i
            self.job_handler.update_job_status(job_id, step['status_update'])
            step_result = self._execute_step_with_strategy(
                job_id, job_info, step, current_step_index, previous_step_result, repo_reader, i, start_from_step
            )
            self.job_handler.save_step_result(job_info, current_step_index, step_result)
            previous_step_result = step_result
            strategy = StepStrategyFactory.create_strategy(step, self.job_handler, self.report_handler)
            if strategy.should_pause_for_approval(job_info, step):
                if not job_info['data'].get('report_blob_url'):
                    self.report_handler.save_generated_report(job_id, job_info, step_result, current_step_index)
                    if not job_info['data'].get('report_blob_url'):
                        raise ValueError(f"[{job_id}] ERRO CRÍTICO: Tentativa de pausar para aprovação sem relatório salvo no Blob Storage.")
                self.job_handler.prepare_for_approval(job_info, current_step_index, step_result)
                self.job_handler.update_job(job_id, job_info)
                return
            if strategy.should_finalize_workflow(job_info, current_step_index):
                self.job_handler.update_job_status(job_id, 'completed')
                return
        if steps_to_run and start_from_step == 0 and job_info['data'].get('analysis_report') and not job_info['data'].get('report_blob_url'):
            self.report_handler.save_report_to_blob(
                job_id,
                job_info,
                job_info['data']['analysis_report'],
                report_generated_by_agent=True
            )
            self.job_handler.update_job(job_id, job_info)

    def _execute_epic_generation_workflow(self, job_id, job_info, workflow, repo_reader, start_from_step):
        previous_step_result = self.job_handler.get_step_result(job_info, start_from_step)
        steps_to_run = workflow.get('steps', [])[start_from_step:]
        for i, step in enumerate(steps_to_run):
            current_step_index = start_from_step + i
            self.job_handler.update_job_status(job_id, step['status_update'])
            step_result = self._execute_step_with_strategy(
                job_id, job_info, step, current_step_index, previous_step_result, repo_reader, i, start_from_step
            )
            self.job_handler.save_step_result(job_info, current_step_index, step_result)
            previous_step_result = step_result
            strategy = StepStrategyFactory.create_strategy(step, self.job_handler, self.report_handler)
            if strategy.should_pause_for_approval(job_info, step):
                if not job_info['data'].get('report_blob_url'):
                    self.report_handler.save_generated_report(job_id, job_info, step_result, current_step_index)
                    if not job_info['data'].get('report_blob_url'):
                        raise ValueError(f"[{job_id}] ERRO CRÍTICO: Tentativa de pausar para aprovação sem relatório salvo no Blob Storage.")
                self.job_handler.prepare_for_approval(job_info, current_step_index, step_result)
                self.job_handler.update_job(job_id, job_info)
                return
        analysis_report = job_info['data'].get('analysis_report')
        organization_url = job_info['data'].get('organization_url')
        project_name = job_info['data'].get('azure_project_name')
        self.epic_and_task_creation_service.create_epics_and_tasks_from_report(
            job_id, job_info, analysis_report, organization_url, project_name
        )
        self.job_handler.update_job_status(job_id, 'completed')
        self.job_handler.update_job(job_id, job_info)

    def _execute_step_with_strategy(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], 
                                    current_step_index: int, previous_step_result: Dict[str, Any], 
                                    repo_reader: ReaderGeral, step_iteration: int, start_from_step: int, batch_steps: Optional[list] = None, agent_params_override: Optional[dict] = None) -> Dict[str, Any]:
        model_para_etapa = step.get('model_name', job_info.get('data', {}).get('model_name'))
        llm_provider = LLMProviderFactory.create_provider(model_para_etapa, self.rag_retriever)
        agent_params = step.get('params', {}).copy() if step.get('params') else {}
        is_comparador_agent = step.get('agent') == 'comparador'
        if is_comparador_agent:
            agent_params.update({
                'repo_name_modernizado': job_info['data'].get('repo_name_modernizado'),
                'branch_name_modernizado': job_info['data'].get('branch_name_modernizado'),
                'repo_name_original': job_info['data'].get('repo_name_original'),
                'branch_name_original': job_info['data'].get('branch_name_original')
            })
        else:
            repo_name = job_info['data'].get('repo_name_modernizado')
            branch_name = job_info['data'].get('branch_name_modernizado')
            agent_params.update({
                'repositorio': repo_name,
                'nome_branch': branch_name
            })
        retornar_lista_arquivos = job_info.get('data', {}).get('retornar_lista_arquivos', False)
        agent_params.update({
            'usar_rag': job_info.get("data", {}).get("usar_rag", False), 
            'model_name': model_para_etapa,
            'repository_type': job_info['data']['repository_type'],
            'retornar_lista_arquivos': retornar_lista_arquivos,
            'modo_adicao_incremental': job_info.get('data', {}).get('modo_adicao_incremental', False),
            'usuario_executor': job_info.get('data', {}).get('usuario_executor')
        })
        agent_params['job_id'] = job_id
        if batch_steps is not None:
            agent_params['current_batch'] = batch_steps
        if agent_params_override:
            agent_params.update(agent_params_override)
        strategy = StepStrategyFactory.create_strategy(step, self.job_handler, self.report_handler)
        result = strategy.execute_step(
            job_id, job_info, step, current_step_index, 
            previous_step_result, repo_reader, llm_provider, agent_params
        )
        return result
