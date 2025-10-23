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
import tools.blob_report_reader as blob_report_reader
from services.azure_board_service import AzureBoardService
from tools.cache_key_builder import build_cache_key_for_report

class WorkflowOrchestrator(IWorkflowOrchestrator):
    def __init__(self, job_manager: IJobManager, blob_storage: IBlobStorageService, 
                 workflow_registry: Dict[str, Any], rag_retriever=None, 
                 job_handler: JobHandler = None, report_handler: ReportHandler = None,
                 commit_handler: CommitHandler = None, data_formatter: DataFormatter = None, secret_manager: Optional[Any] = None,
                 cache_service=None, dependency_container=None):
        self.workflow_registry = workflow_registry
        self.rag_retriever = rag_retriever or AzureAISearchRAGRetriever()
        self.job_handler = job_handler or JobHandler(job_manager)
        self.cache_service = cache_service
        self.report_handler = report_handler or ReportHandler(blob_storage, cache_service=self.cache_service)
        self.commit_handler = commit_handler or CommitHandler()
        self.data_formatter = data_formatter or DataFormatter()
        self.secret_manager = secret_manager or AzureSecretManager()
        self.dependency_container = dependency_container

    def _save_generated_report(self, job_id: str, job_info: Dict[str, Any], step_result: Dict[str, Any], current_step_index: int) -> bool:
        print(f"[{job_id}] [DEBUG] Entrando em _save_generated_report para o step {current_step_index}.")
        report_text = self.report_handler.extract_report_text(step_result)
        if not report_text or len(report_text.strip()) == 0:
            print(f"[{job_id}] ERRO: Relatório gerado pelo agente está vazio no step {current_step_index}.")
            return False
        print(f"[{job_id}] [DEBUG] Salvando relatório gerado pelo agente. gerar_relatorio_apenas: {job_info['data'].get(JobFields.GERAR_RELATORIO_APENAS)}, tamanho do relatório: {len(report_text)}")
        job_info['data']['analysis_report'] = report_text
        print(f"[{job_id}] [DEBUG] Chamando save_report_to_blob para salvar o relatório do step {current_step_index}.")
        url = self.report_handler.save_report_to_blob(job_id, job_info, report_text)
        print(f"[{job_id}] [DEBUG] save_report_to_blob retornou url: {url}")
        if not url:
            raise ValueError(f"[{job_id}] ERRO CRÍTICO: Relatório não foi salvo no Blob Storage")
        print(f"[{job_id}] Relatório salvo com sucesso: {url}")
        job_info['data']['report_blob_url'] = url
        self.job_handler.update_job(job_id, job_info)
        try:
            if job_info['data'].get('report_blob_url'):
                self.report_handler.blob_storage.update_job_tracker(job_info['data']['report_blob_url'], job_id)
        except Exception as e:
            print(f"[WorkflowOrchestrator] Warning: Failed to update job tracker after saving report: {e}")
        return True

    def execute_workflow(self, job_id: str, start_from_step: int = 0) -> None:
        job_info = self.job_handler.get_job_info(job_id)
        workflow = self.workflow_registry.get(job_info['data']['original_analysis_type'])
        if not workflow:
            raise ValueError("Workflow não encontrado.")
        try:
            analysis_name = job_info['data'].get('analysis_name')
            projeto = job_info['data'].get('projeto')
            analysis_type = job_info['data'].get('original_analysis_type')
            repository_type = job_info['data'].get('repository_type')
            repo_name = job_info['data'].get('repo_name')
            branch_name = job_info['data'].get('branch_name_modernizado')
            cache_key = build_cache_key_for_report(projeto, analysis_type, repository_type, repo_name, branch_name, analysis_name)
            if start_from_step == 0:
                report_from_blob = blob_report_reader.read_report_from_blob(
                    projeto=projeto,
                    analysis_type=analysis_type,
                    repository_type=repository_type,
                    repo_name=repo_name,
                    branch_name=branch_name,
                    analysis_name=analysis_name
                )
                if report_from_blob is not None and report_from_blob.strip():
                    job_info['data']['analysis_report'] = report_from_blob
                    from tools.blob_report_path_builder import build_report_blob_path
                    from os import getenv
                    projeto_clean = projeto if projeto else "unknown"
                    analysis_type_clean = analysis_type if analysis_type else "unknown"
                    repository_type_clean = repository_type if repository_type else "unknown"
                    repo_name_clean = repo_name if repo_name else "unknown"
                    branch_name_clean = branch_name if branch_name else "unknown"
                    analysis_name_clean = analysis_name if analysis_name else "unknown"
                    blob_path = build_report_blob_path(projeto_clean, analysis_type_clean, repository_type_clean, repo_name_clean, branch_name_clean, analysis_name_clean)
                    container_name = getenv('AZURE_STORAGE_CONTAINER_NAME')
                    account_url = getenv('AZURE_STORAGE_ACCOUNT_URL')
                    if account_url and container_name:
                        report_blob_url = f"{account_url}/{container_name}/{blob_path}"
                    elif container_name:
                        report_blob_url = f"/{container_name}/{blob_path}"
                    else:
                        report_blob_url = None
                    job_info['data']['report_blob_url'] = report_blob_url
                    self.job_handler.update_job(job_id, job_info)
                    print(f"[{job_id}] [DEBUG] Relatório encontrado no Blob Storage no step 0. Workflow pausado para aprovação.")
                    self.handle_approval_step(job_id, job_info, 0, {'relatorio': report_from_blob})
                    return
                else:
                    print(f"[{job_id}] [DEBUG] Relatório NÃO encontrado no Blob Storage no step 0. Prosseguindo para geração do relatório pelo agente.")
            repository_type = job_info['data']['repository_type']
            repo_name = job_info['data'].get('repo_name')
            repository_provider = get_repository_provider_explicit(repository_type)
            cache_service = self.cache_service or (self.dependency_container.get_redis_cache_service() if self.dependency_container else None)
            repo_reader = ReaderGeral(repository_provider=repository_provider, cache_service=cache_service)
            previous_step_result = self.job_handler.get_step_result(job_info, start_from_step)
            steps_to_run = workflow.get('steps', [])[start_from_step:]
            executar_incremental = job_info['data'].get(JobFields.EXECUTAR_STEPS_INCREMENTALMENTE, False)
            max_steps_per_batch = job_info['data'].get(JobFields.MAX_STEPS_PER_BATCH, 3)
            gerar_relatorio_apenas = job_info['data'].get(JobFields.GERAR_RELATORIO_APENAS, False)
            if executar_incremental and start_from_step == 1:
                if not job_info['data'].get(JobFields.STEP_BATCHES):
                    report_text = job_info['data'].get('analysis_report')
                    if not report_text or not report_text.strip():
                        raise ValueError(f"[{job_id}] ERRO: Relatório aprovado não encontrado para parsing incremental.")
                    step_batches = IncrementalStepExecutorService.get_step_batches_from_report(report_text, max_steps_per_batch=max_steps_per_batch)
                    job_info['data'][JobFields.STEP_BATCHES] = step_batches
                    job_info['data'][JobFields.CURRENT_BATCH_INDEX] = 0
                    job_info['data'][JobFields.BATCH_RESULTS] = []
                    self.job_handler.update_job(job_id, job_info)
                    print(f"[{job_id}] [INCREMENTAL] step_batches inicializados com {len(step_batches)} batches.")
            if not executar_incremental and not gerar_relatorio_apenas:
                raise ValueError("Modo não-incremental descontinuado. Use executar_steps_incrementalmente=True ou gerar_relatorio_apenas=True.")
            for i, step in enumerate(steps_to_run):
                current_step_index = start_from_step + i
                print(f"[{job_id}] Executando step {current_step_index}/{len(workflow.get('steps', []))-1}")
                self.job_handler.update_job_status(job_id, step['status_update'])
                step_result = None
                if executar_incremental and current_step_index == 1:
                    step_batches = job_info['data'].get(JobFields.STEP_BATCHES)
                    if step_batches is None:
                        report_text = job_info['data'].get('analysis_report')
                        if not report_text or not report_text.strip():
                            raise ValueError(f"[{job_id}] ERRO: Relatório aprovado não encontrado para parsing incremental.")
                        step_batches = IncrementalStepExecutorService.get_step_batches_from_report(report_text, max_steps_per_batch=max_steps_per_batch)
                        job_info['data'][JobFields.STEP_BATCHES] = step_batches
                        job_info['data'][JobFields.CURRENT_BATCH_INDEX] = 0
                        job_info['data'][JobFields.BATCH_RESULTS] = []
                        self.job_handler.update_job(job_id, job_info)
                        print(f"[{job_id}] [INCREMENTAL] step_batches inicializados com {len(step_batches)} batches.")
                    current_batch_index = job_info['data'].get(JobFields.CURRENT_BATCH_INDEX, 0)
                    batch_results = job_info['data'].get(JobFields.BATCH_RESULTS, [])
                    total_batches = len(step_batches)
                    for batch_idx in range(current_batch_index, total_batches):
                        try:
                            batch = step_batches[batch_idx]
                            print(f"[{job_id}] [INCREMENTAL] Batch {batch_idx+1}/{total_batches}: {len(batch)} steps.")
                            agent_params = step.get('params', {}).copy() if step.get('params') else {}
                            agent_params['current_batch'] = batch
                            agent_params['total_batches'] = total_batches
                            result = self._execute_step_with_strategy(
                                job_id, job_info, step, current_step_index, previous_step_result, repo_reader, i, start_from_step, agent_params_override=agent_params
                            )
                            batch_results.append(result)
                        except Exception as e:
                            error_message = f"ERRO FATAL no batch {batch_idx + 1}: {e}. Pulando para o próximo batch."
                            print(f"[{job_id}] {error_message}")
                            if 'failed_batches' not in job_info['data']:
                                job_info['data']['failed_batches'] = []
                            job_info['data']['failed_batches'].append({
                                "batch_index": batch_idx + 1,
                                "error": str(e)
                            })
                            continue 
                        finally:
                            job_info['data'][JobFields.BATCH_RESULTS] = batch_results
                            job_info['data'][JobFields.CURRENT_BATCH_INDEX] = batch_idx + 1
                            self.job_handler.update_job(job_id, job_info)
                    print(f"[{job_id}] [INCREMENTAL] Todos os batches processados.")
                    previous_step_result = {'incremental_results': batch_results}
                    break
                else:
                    step_result = self._execute_step_with_strategy(
                        job_id, job_info, step, current_step_index, previous_step_result, repo_reader, i, start_from_step
                    )
                    if current_step_index == 0:
                        report_text = self.report_handler.extract_report_text(step_result)
                        if report_text and report_text.strip():
                            self.report_handler.save_report_to_cache(cache_key, report_text)
                            self._save_generated_report(job_id, job_info, step_result, current_step_index)
                            if step.get('requires_approval', False):
                                self.handle_approval_step(job_id, job_info, current_step_index, step_result)
                                return
                        else:
                            print(f"[{job_id}] [DEBUG] Relatório gerado pelo agente está vazio no step 0.")
                            return
                        previous_step_result = step_result
                    if gerar_relatorio_apenas:
                        self.job_handler.update_job_status(job_id, 'completed')
                        print(f"[{job_id}] [DEBUG] gerar_relatorio_apenas=True detectado após step 0. Status atualizado para completed. Encerrando workflow.")
                        return
                    previous_step_result = step_result
            if not gerar_relatorio_apenas:
                self._finalize_workflow(job_id, job_info, workflow, previous_step_result, repository_type, repo_name)
        except Exception as e:
            self.job_handler.handle_job_error(job_id, e, 'workflow')

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
            if not job_info['data'].get('criar_epicos_azure'):
                branch_name = job_info['data'].get('branch_name_modernizado')
                agent_params['nome_branch'] = branch_name
            agent_params['repositorio'] = repo_name
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
        strategy = StepStrategyFactory.create_strategy(step, self.job_handler)
        result = strategy.execute_step(
            job_id, job_info, step, current_step_index, 
            previous_step_result, repo_reader, llm_provider, agent_params
        )
        if current_step_index == 0:
            print(f"[{job_id}] [DEBUG] Salvando relatório gerado pelo agente no step 0.")
            report_text = self.report_handler.extract_report_text(result)
            if report_text and report_text.strip():
                self._save_generated_report(job_id, job_info, result, current_step_index)
                print(f"[{job_id}] [DEBUG] Relatório salvo com sucesso no step {current_step_index}.")
                if step.get('requires_approval', False):
                    self.handle_approval_step(job_id, job_info, current_step_index, result)
                    return result
            else:
                print(f"[{job_id}] [DEBUG] Relatório gerado pelo agente está vazio no step 0.")
                return result
        if step.get('requires_approval', False):
            return result
        return result

    def handle_approval_step(self, job_id: str, job_info: Dict[str, Any], step_index: int, step_result: Dict[str, Any]) -> None:
        print(f"[{job_id}] Etapa requer aprovação.")
        report_text = self.report_handler.extract_report_text(step_result)
        job_info['data']['analysis_report'] = report_text
        job_info['status'] = 'pending_approval'
        self.job_handler.set_paused_step(job_info, step_index)
        self.job_handler.update_job(job_id, job_info)

    def _finalize_workflow(self, job_id: str, job_info: Dict[str, Any], workflow: Dict[str, Any], 
                           final_result: Dict[str, Any], repository_type: str, repo_name: str) -> None:
        if job_info['data'].get('criar_epicos_azure'):
            print(f"[{job_id}] [AZURE_EPICS] Iniciando criação de épicos no Azure DevOps Board...")
            organization = job_info['data'].get('azure_organization')
            project = job_info['data'].get('azure_project')
            report = job_info['data'].get('analysis_report')
            azure_board_service = AzureBoardService(organization, project, self.secret_manager)
            created_epics = azure_board_service.create_epics(report)
            job_info['data']['epicos_criados'] = created_epics
            self.job_handler.update_job(job_id, job_info)
            print(f"[{job_id}] [AZURE_EPICS] Épicos criados: {created_epics}")
        else:
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

    def _get_access_token(self, repository_type: str, repo_name: str) -> Optional[str]:
        print(f"[WorkflowOrchestrator] Obtendo token. repository_type={repository_type}, repo_name={repo_name}")
        if repository_type == 'azure':
            parts = repo_name.split('/')
            if len(parts) != 3:
                raise ValueError(f"Nome do repositório '{repo_name}' tem formato inválido para Azure.")
            org_name = parts[0]
            platform = 'Azure'
        elif repository_type == 'github':
            org_name = repo_name.strip().split('/')[0]
            platform = 'GitHub'
        elif repository_type == 'gitlab':
            org_name = repo_name.strip().split('/')[0]
            platform = 'GitLab'
        else:
            raise ValueError(f"Tipo de repositório '{repository_type}' não suportado para obtenção de token.")
        token_secret_name = f"{platform.lower()}-token-{org_name}"
        try:
            token = self.secret_manager.get_secret(token_secret_name)
            print(f"[WorkflowOrchestrator] Token obtido com sucesso. secret_name={token_secret_name}, token presente: {bool(token)}")
            return token
        except Exception:
            print(f"[WorkflowOrchestrator] Falha ao obter token. secret_name={token_secret_name}, tentando fallback...")
            try:
                token = self.secret_manager.get_secret(f"{platform.lower()}-token")
                print(f"[WorkflowOrchestrator] Token obtido com sucesso. secret_name={platform.lower()}-token, token presente: {bool(token)}")
                return token
            except Exception:
                raise ValueError(f"Não foi possível obter token para {platform} ({org_name})")
