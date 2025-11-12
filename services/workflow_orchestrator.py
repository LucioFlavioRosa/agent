import re
import json
import time
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
from tools.azure_secret_manager import AzureSecretManager
from services.azure_board_service import AzureBoardService
import traceback
from services.task_discussion_updater_service import TaskDiscussionUpdaterService

class WorkflowOrchestrator(IWorkflowOrchestrator):
    def __init__(self, job_manager: IJobManager, blob_storage: IBlobStorageService, 
                 workflow_registry: Dict[str, Any], rag_retriever=None, 
                 job_handler: JobHandler = None, report_handler: ReportHandler = None,
                 commit_handler: CommitHandler = None, data_formatter: DataFormatter = None, secret_manager: Optional[Any] = None,
                 cache_service=None, dependency_container=None, azure_board_service=None):
        self.workflow_registry = workflow_registry
        self.rag_retriever = rag_retriever or AzureAISearchRAGRetriever()
        self.job_handler = job_handler or JobHandler(job_manager)
        self.cache_service = cache_service
        self.report_handler = report_handler or ReportHandler(blob_storage, cache_service=self.cache_service)
        self.commit_handler = commit_handler or CommitHandler()
        self.data_formatter = data_formatter or DataFormatter()
        self.secret_manager = secret_manager or AzureSecretManager()
        self.dependency_container = dependency_container
        self.azure_board_service = azure_board_service

    def execute_workflow(self, job_id: str, start_from_step: int = 0) -> None:
        job_info = self.job_handler.get_job_info(job_id)
        repo_name_modernizado = job_info['data'].get('repo_name_modernizado')
        analysis_type = job_info['data'].get('original_analysis_type', '')
        if not repo_name_modernizado and analysis_type not in ['criacao_epicos_azure_devops', 'criacao_tarefas_azure_devops', 'revisor_tarefas', 'criacao_features_azure_devops']:
            raise ValueError("O campo 'repo_name_modernizado' é obrigatório em job_info['data'] para execução do workflow.")
        workflow = self.workflow_registry.get(job_info['data']['original_analysis_type'])
        if not workflow:
            raise ValueError("Workflow não encontrado.")
        try:
            analysis_name = job_info['data'].get('analysis_name')
            projeto = job_info['data'].get('projeto')
            repository_type = job_info['data'].get('repository_type')
            repo_name = job_info['data'].get('repo_name')
            branch_name = job_info['data'].get('branch_name_modernizado')

            if start_from_step == 0 and analysis_type == 'criacao_tarefas_azure_devops':
                print(f"[{job_id}] [DEBUG] Step 0 (criacao_tarefas_azure_devops): feature_id={job_info['data'].get('feature_id')}")
                feature_id = job_info['data'].get('feature_id')
                if not feature_id:
                    raise ValueError(f"[{job_id}] ERRO: feature_id ausente em job_info['data'] para analysis_type == 'criacao_tarefas_azure_devops'.")
                organization = job_info['data'].get('organization') or job_info['data'].get('azure_organization')
                project = job_info['data'].get('project') or job_info['data'].get('azure_project')
                if not organization or not project:
                    raise ValueError(f"[{job_id}] ERRO: organization ou project ausentes para análise de tarefas Azure DevOps.")
                azure_board_service = AzureBoardService(organization, project, self.secret_manager)
                print(f"[{job_id}] [DEBUG] Lendo dados da feature do Azure DevOps: feature_id={feature_id}")
                feature_data = azure_board_service.read_feature(feature_id)
                print(f"[{job_id}] [DEBUG] Dados completos da feature lida: {json.dumps(feature_data, ensure_ascii=False)}")
                job_info['data']['feature_title'] = feature_data.get('title')
                job_info['data']['feature_description'] = feature_data.get('description')
                job_info['data']['feature_acceptance_criteria'] = feature_data.get('acceptance_criteria')
                job_info['data']['feature_data'] = feature_data
                if not job_info['data']['feature_title'] or not job_info['data']['feature_description'] or not job_info['data']['feature_acceptance_criteria']:
                    raise ValueError(f"[{job_id}] ERRO: Campos obrigatórios da feature ausentes ou vazios após leitura. title={job_info['data']['feature_title']}, description={job_info['data']['feature_description']}, acceptance_criteria={job_info['data']['feature_acceptance_criteria']}")
                print(f"[{job_id}] [DEBUG] Dados da feature propagados para job_info['data']: {json.dumps(feature_data, ensure_ascii=False)[:200]}...")
            # ... resto do método permanece igual ...
