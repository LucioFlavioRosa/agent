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

class WorkflowOrchestrator(IWorkflowOrchestrator):
    def __init__(self, job_manager: IJobManager, blob_storage: IBlobStorageService, 
                 workflow_registry: Dict[str, Any], rag_retriever=None, 
                 job_handler: JobHandler = None, report_handler: ReportHandler = None,
                 commit_handler: CommitHandler = None, data_formatter: DataFormatter = None, secret_manager: Optional[Any] = None,
                 cache_service=None, dependency_container=None):
        self.workflow_registry = workflow_registry
        self.rag_retriever = rag_retriever or AzureAISearchRAGRetriever()
        self.job_handler = job_handler or JobHandler(job_manager)
        self.report_handler = report_handler or ReportHandler(blob_storage)
        self.commit_handler = commit_handler or CommitHandler()
        self.data_formatter = data_formatter or DataFormatter()
        self.secret_manager = secret_manager or AzureSecretManager()
        self.cache_service = cache_service
        self.dependency_container = dependency_container

    # ... outros métodos permanecem inalterados ...

    def _finalize_workflow(self, job_id: str, job_info: Dict[str, Any], workflow: Dict[str, Any], 
                           final_result: Dict[str, Any], repository_type: str, repo_name: str) -> None:
        # FLUXO EXCLUSIVO PARA GERAÇÃO DE EPICOS E TAREFAS (SEM COMMIT)
        if job_info['data'].get('gerar_epicos') is True and job_info['data'].get('criar_cards_azure') is True:
            try:
                analysis_report = job_info['data'].get('analysis_report')
                epicos = EpicoParserService.parse_epicos_from_report(analysis_report)
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
                azure_boards_service = self.dependency_container.get_azure_boards_service(organization_url, project_name)
                cards_criados = azure_boards_service.criar_multiplos_cards(epicos)
                job_info['data']['cards_criados'] = cards_criados
                job_info['data']['cards_creation_errors'] = [c for c in cards_criados if c.get('erro')] if cards_criados else []
                self.job_handler.update_job_status(job_id, 'completed')
                self.job_handler.update_job(job_id, job_info)
                return
            except Exception as e:
                job_info['data']['cards_creation_errors'] = [str(e)]
                self.job_handler.update_job_status(job_id, 'failed')
                self.job_handler.update_job(job_id, job_info)
                return
        # FLUXO DE GERAÇÃO DE TAREFAS PARA EPICOS APROVADOS (SEM COMMIT)
        if job_info['data'].get(JobFields.GERAR_TAREFAS) is True and job_info['data'].get('criar_cards_azure') is True:
            try:
                analysis_report = job_info['data'].get('analysis_report')
                observacoes_aprovacao = job_info['data'].get('instrucoes_extras_aprovacao')
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
                azure_boards_service = self.dependency_container.get_azure_boards_service(organization_url, project_name)
                tarefas_criadas = []
                tarefas_creation_errors = []
                # O parsing dos épicos aprovados deve ser feito a partir das observações de aprovação
                epicos_aprovados = []
                if observacoes_aprovacao:
                    # Espera-se que as observações contenham os IDs dos épicos aprovados, separados por vírgula ou linha
                    for line in observacoes_aprovacao.splitlines():
                        line = line.strip()
                        if line.startswith('E') and len(line) >= 3:
                            epicos_aprovados.append(line.split()[0])
                        elif ',' in line:
                            epicos_aprovados.extend([e.strip() for e in line.split(',') if e.strip().startswith('E')])
                if not epicos_aprovados:
                    raise ValueError("Não foi possível identificar os épicos aprovados a partir das observações de aprovação.")
                for epico_id in epicos_aprovados:
                    tarefas = TarefaParserService.parse_tarefas_from_report(analysis_report, epico_id)
                    resultado = azure_boards_service.criar_multiplas_tarefas(tarefas, epico_id)
                    tarefas_criadas.extend(resultado)
                    tarefas_creation_errors.extend([r for r in resultado if r.get('erro')])
                job_info['data']['tarefas_criadas'] = tarefas_criadas
                job_info['data']['tarefas_creation_errors'] = tarefas_creation_errors
                self.job_handler.update_job_status(job_id, 'completed')
                self.job_handler.update_job(job_id, job_info)
                return
            except Exception as e:
                job_info['data']['tarefas_creation_errors'] = [str(e)]
                self.job_handler.update_job_status(job_id, 'failed')
                self.job_handler.update_job(job_id, job_info)
                return
        # ... restante do método permanece inalterado ...
        executar_incremental = job_info['data'].get(JobFields.EXECUTAR_STEPS_INCREMENTALMENTE, False)
        if executar_incremental and JobFields.BATCH_RESULTS in job_info['data']:
            batch_results = job_info['data'][JobFields.BATCH_RESULTS]
            total_batches = len(batch_results)
            total_steps = sum(len(batch) if isinstance(batch, list) else 1 for batch in batch_results)
            print(f"[{job_id}] [INCREMENTAL] Finalizando workflow incremental. Batches processados: {total_batches}, Steps executados: {total_steps}.")
            final_result = IncrementalStepExecutorService.merge_all_batches(batch_results)
        dados_finais_formatados = self.data_formatter.format_incremental_result_for_commit(final_result)
        self.job_handler.update_job_status(job_id, 'committing_to_github')
        self.commit_handler.execute_commits(job_id, job_info, dados_finais_formatados, repository_type, repo_name)
        print(f"[{job_id}] [DEBUG] Após execute_commits: executar_build_dotnet={job_info['data'].get('executar_build_dotnet')}, commit_details presente: {bool(job_info['data'].get('commit_details'))}")
        if job_info['data'].get('executar_build_dotnet', False):
            commit_details = job_info['data'].get('commit_details', [])
            build_errors = []
            for idx, commit in enumerate(commit_details):
                if 'build_result' not in commit:
                    print(f"[{job_id}] [ERRO CRÍTICO] build_result ausente no commit_details[{idx}] quando executar_build_dotnet=True")
                if 'build_errors' not in commit:
                    print(f"[{job_id}] [ERRO CRÍTICO] build_errors ausente no commit_details[{idx}] quando executar_build_dotnet=True")
                errors = commit.get('build_errors')
                if errors:
                    build_errors.extend(errors)
            if build_errors:
                job_info['data']['build_errors'] = build_errors
            else:
                job_info['data']['build_errors'] = None
            self.job_handler.update_job(job_id, job_info)
        else:
            job_info['data']['build_errors'] = None
        self.job_handler.update_job(job_id, job_info)
        print(f"[{job_id}] DIAGNÓSTICO - Job atualizado no job store")
        if job_info['data'].get('executar_build_dotnet', False):
            commit_details = job_info['data'].get('commit_details', [])
            for idx, commit in enumerate(commit_details):
                if 'build_result' not in commit:
                    print(f"[{job_id}] [ERRO CRÍTICO] build_result ausente no commit_details[{idx}] quando executar_build_dotnet=True")
                if 'build_errors' not in commit:
                    print(f"[{job_id}] [ERRO CRÍTICO] build_errors ausente no commit_details[{idx}] quando executar_build_dotnet=True")
        self.job_handler.update_job_status(job_id, 'completed')
