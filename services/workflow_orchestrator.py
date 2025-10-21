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

    # ... outras funções ...

    def _finalize_workflow(self, job_id: str, job_info: Dict[str, Any], workflow: Dict[str, Any], 
                           final_result: Dict[str, Any], repository_type: str, repo_name: str) -> None:
        if job_info['data'].get('original_analysis_type') == 'geracao_epicos_a_partir_de_reuniao':
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

                instrucoes_extras = job_info['data'].get('instrucoes_extras')
                epicos_aprovados_nomes = None
                if instrucoes_extras:
                    ids_regex = re.findall(r'\bE\d{2,}\b', instrucoes_extras)
                    titulos_regex = re.findall(r'epico com titulo ([\w\s\-]+)', instrucoes_extras, re.IGNORECASE)
                    ids_text = re.findall(r'epico com id ([\w\d]+)', instrucoes_extras, re.IGNORECASE)
                    epicos_aprovados_nomes = list(set(ids_regex + ids_text + titulos_regex))
                    if not epicos_aprovados_nomes:
                        try:
                            parsed = json.loads(instrucoes_extras)
                            if isinstance(parsed, list):
                                epicos_aprovados_nomes = [str(e) for e in parsed]
                            elif isinstance(parsed, dict) and 'epicos_aprovados' in parsed:
                                epicos_aprovados_nomes = [str(e) for e in parsed['epicos_aprovados']]
                            else:
                                epicos_aprovados_nomes = [s.strip() for s in instrucoes_extras.split(',') if s.strip()]
                        except Exception:
                            epicos_aprovados_nomes = [s.strip() for s in instrucoes_extras.split(',') if s.strip()]
                    if epicos_aprovados_nomes:
                        print(f"[{job_id}] IDs/títulos extraídos de instrucoes_extras: {epicos_aprovados_nomes}")
                epicos_a_processar = epicos
                if epicos_aprovados_nomes:
                    epicos_a_processar = [e for e in epicos if (e.id in epicos_aprovados_nomes or e.titulo in epicos_aprovados_nomes)]
                    print(f"[{job_id}] Filtrando épicos aprovados: {[e.id for e in epicos_a_processar]} / {[e.titulo for e in epicos_a_processar]}")
                else:
                    print(f"[{job_id}] instrucoes_extras não menciona épicos específicos. Todos os épicos do relatório serão processados.")

                cards_criados = []
                tarefas_criadas = []
                tarefas_creation_errors = []
                for epico in epicos_a_processar:
                    card_result = azure_boards_service.criar_card_epico(epico)
                    cards_criados.append(card_result)
                    tarefas = TarefaParserService.parse_tarefas_from_report(analysis_report, epico_id=epico.id, epico_nome=epico.titulo)
                    print(f"[{job_id}] Tarefas parseadas para épico id={epico.id}, titulo={epico.titulo}: {len(tarefas)}")
                    if tarefas:
                        tarefas_result = azure_boards_service.criar_multiplas_tarefas(tarefas, epico_nome=epico.titulo)
                        tarefas_criadas.extend(tarefas_result)
                        tarefas_creation_errors.extend([r for r in tarefas_result if r.get('erro')])
                    else:
                        print(f"[{job_id}] Nenhuma tarefa encontrada para épico id={epico.id}, titulo={epico.titulo}")
                job_info['data']['cards_criados'] = cards_criados
                job_info['data']['cards_creation_errors'] = [c for c in cards_criados if c.get('erro')] if cards_criados else []
                job_info['data']['tarefas_criadas'] = tarefas_criadas
                job_info['data']['tarefas_creation_errors'] = tarefas_creation_errors
                print(f"[{job_id}] cards_criados: {cards_criados}")
                print(f"[{job_id}] tarefas_criadas: {tarefas_criadas}")
                print(f"[{job_id}] tarefas_creation_errors: {tarefas_creation_errors}")
                print(f"[{job_id}] Atualizando status do job para completed...")
                self.job_handler.update_job_status(job_id, 'completed')
                self.job_handler.update_job(job_id, job_info)
                print(f"[{job_id}] Status do job atualizado para completed.")
                return
            except Exception as e:
                print(f"[{job_id}] ERRO CRÍTICO durante a criação de épicos/tarefas: {e}")
                job_info['data']['cards_creation_errors'] = [str(e)]
                job_info['data']['tarefas_creation_errors'] = [str(e)]
                self.job_handler.update_job_status(job_id, 'failed')
                self.job_handler.update_job(job_id, job_info)
                return
        # ... restante da função ...
