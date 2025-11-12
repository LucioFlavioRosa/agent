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

    def _save_generated_report(self, job_id: str, job_info: Dict[str, Any], step_result: Dict[str, Any], current_step_index: int) -> bool:
        print(f"[{job_id}] [DEBUG] Entrando em _save_generated_report para step {current_step_index}.")
        report_text = self.report_handler.extract_report_text(step_result)
        print(f"[{job_id}] [DEBUG] extract_report_text retornou: {str(report_text)[:200]}...")
        if not report_text or len(report_text.strip()) == 0:
            print(f"[{job_id}] ERRO: Relatório gerado pelo agente está vazio no step {current_step_index}.")
            return False
        job_info['data']['analysis_report'] = report_text
        url = self.report_handler.save_report_to_blob(job_id, job_info, report_text)
        print(f"[{job_id}] [DEBUG] save_report_to_blob retornou url: {url}")
        if not url:
            raise ValueError(f"[{job_id}] ERRO CRÍTICO: Relatório não foi salvo no Blob Storage")
        job_info['data']['report_blob_url'] = url
        self.job_handler.update_job(job_id, job_info)
        try:
            if job_info['data'].get('report_blob_url'):
                self.report_handler.blob_storage.update_job_tracker(job_info['data']['report_blob_url'], job_id)
        except Exception as e:
            print(f"[WorkflowOrchestrator] Warning: Failed to update job tracker after saving report: {e}")
        print(f"[{job_id}] [DEBUG] _save_generated_report finalizado com sucesso para step {current_step_index}.")
        return True
    
    def execute_workflow(self, job_id: str, start_from_step: int = 0) -> None:
        job_info = self.job_handler.get_job_info(job_id)
        repo_name_modernizado = job_info['data'].get('repo_name_modernizado')
        
        # Ajuste: Nem todos os workflows (ex: Azure DevOps) precisam de 'repo_name_modernizado'
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
            
            if start_from_step > 0 and analysis_type == 'criacao_features_azure_devops':
                print(f"[{job_id}] [DEBUG] Entrando no fluxo de criação de features Azure. epic_id={job_info['data'].get('epic_id')}")
                epic_id = job_info['data'].get('epic_id')
                organization = job_info['data'].get('organization') or job_info['data'].get('azure_organization')
                project = job_info['data'].get('project') or job_info['data'].get('azure_project')
                report = job_info['data'].get('analysis_report')
                print(f"[{job_id}] [DEBUG] Dados para criação de features: epic_id={epic_id}, organization={organization}, project={project}, tamanho do relatório={len(report) if report else 0}")
                if not epic_id:
                    raise ValueError(f"[{job_id}] ERRO: epic_id ausente em job_info['data'] para analysis_type == 'criacao_features_azure_devops'.")
                if not report or not report.strip():
                    raise ValueError(f"[{job_id}] ERRO: Relatório de features ausente ou vazio para criação de features no Azure.")
                azure_board_service = AzureBoardService(organization, project, self.secret_manager)
                print(f"[{job_id}] [DEBUG] Chamando AzureBoardService.create_features_from_epic com epic_id={epic_id}")
                created_features = azure_board_service.create_features_from_epic(epic_id, report)
                print(f"[{job_id}] [DEBUG] Resultado AzureBoardService.create_features_from_epic: {created_features}")
                
                if created_features and any('error' in feature for feature in created_features):
                    error_message = next((feature['error'] for feature in created_features if 'error' in feature), "Erro desconhecido ao criar features no Azure.")
                    print(f"[{job_id}] [ERROR] Falha detectada ao criar features no Azure: {error_message}")
                    job_info['data']['features_criadas_erro'] = created_features
                    self.job_handler.update_job(job_id, job_info)
                    self.job_handler.update_job_status(job_id, 'failed')
                    return
                if created_features is not None and len(created_features) == 0:
                    print(f"[{job_id}] [ERROR] Nenhuma feature foi criada. Verifique o parsing do relatório e a conexão com o Azure DevOps.")
                    job_info['data']['error_details'] = 'Nenhuma feature foi criada. Verifique o parsing do relatório e a conexão com o Azure DevOps.'
                    self.job_handler.update_job(job_id, job_info)
                    self.job_handler.update_job_status(job_id, 'failed')
                    return
                    
                job_info['data']['features_criadas'] = created_features
                self.job_handler.update_job(job_id, job_info)
                print(f"[{job_id}] [AZURE_FEATURES] Features criadas: {created_features}")
                print(f"[{job_id}] [DEBUG] Atualizando status do job para 'completed' após criação de features Azure.")
                self.job_handler.update_job_status(job_id, 'completed')
                print(f"[{job_id}] [DEBUG] Workflow finalizado após criação de features Azure.")
                return
            
            if analysis_type == 'revisor_tarefas':
                print(f"[{job_id}] [DEBUG] Step 0 (revisor_tarefas): task_id={job_info['data'].get('task_id')}, epic_id={job_info['data'].get('epic_id')}, status_update={workflow.get('steps', [])[0].get('status_update')}")
                if start_from_step == 0:
                    task_id = job_info['data'].get('task_id')
                    print(f"[{job_id}] [DEBUG] Step 0 (revisor_tarefas) - task_id presente? {task_id is not None}, valor: {task_id}")
                    if not task_id:
                        raise ValueError(f"[{job_id}] ERRO: task_id ausente em job_info['data'] para analysis_type == 'revisor_tarefas'.")
            
            # ==================================================================
            # == MUDANÇA 1: Bloco 'criacao_tarefas_azure_devops' atualizado ==
            # ==================================================================
            if start_from_step > 0 and analysis_type == 'criacao_tarefas_azure_devops':
                print(f"[{job_id}] [DEBUG] Entrando no fluxo de criação de tarefas Azure (ligadas à feature).")
                organization = job_info['data'].get('organization') or job_info['data'].get('azure_organization')
                project = job_info['data'].get('project') or job_info['data'].get('azure_project')
                
                # Pega o feature_id (em vez do epic_id)
                feature_id = job_info['data'].get('feature_id')
                report = job_info['data'].get('analysis_report')
                
                if not feature_id:
                    raise ValueError(f"[{job_id}] ERRO: feature_id ausente em job_info['data'] para analysis_type == 'criacao_tarefas_azure_devops'.")
                if not report or not report.strip():
                    raise ValueError(f"[{job_id}] ERRO: Relatório de tarefas ausente ou vazio para criação de tarefas no Azure.")

                print(f"[{job_id}] [DEBUG] Dados para criação de tarefas: feature_id={feature_id}, organization={organization}, project={project}, tamanho do relatório={len(report) if report else 0}")
                
                azure_board_service = AzureBoardService(organization, project, self.secret_manager)
                
                # Chama a nova função (que você precisará adicionar ao AzureBoardService)
                print(f"[{job_id}] [DEBUG] Chamando AzureBoardService.create_tasks_from_report_for_feature com feature_id={feature_id}")
                
                # NOTA: Você deve adicionar a função 'create_tasks_from_report_for_feature' ao seu AzureBoardService.py
                # Veja a Seção 2 desta resposta para o código.
                created_tasks = azure_board_service.create_tasks_from_report_for_feature(feature_id, report)
                
                print(f"[{job_id}] [DEBUG] Resultado AzureBoardService.create_tasks_from_report_for_feature: {created_tasks}")
                
                if created_tasks and any('error' in task for task in created_tasks):
                    error_message = next((task['error'] for task in created_tasks if 'error' in task), "Erro desconhecido ao criar tarefas no Azure.")
                    print(f"[{job_id}] [ERROR] Falha detectada ao criar tarefas no Azure: {error_message}")
                    job_info['data']['tarefas_criadas_erro'] = created_tasks
                    self.job_handler.update_job(job_id, job_info)
                    self.job_handler.update_job_status(job_id, 'failed')
                    return
                if created_tasks is not None and len(created_tasks) == 0:
                    print(f"[{job_id}] [ERROR] Nenhuma tarefa foi criada. Verifique o parsing do relatório e a conexão com o Azure DevOps.")
                    job_info['data']['error_details'] = 'Nenhuma tarefa foi criada. Verifique o parsing do relatório e a conexão com o Azure DevOps.'
                    self.job_handler.update_job(job_id, job_info)
                    self.job_handler.update_job_status(job_id, 'failed')
                    return
                    
                job_info['data']['tarefas_criadas'] = created_tasks
                self.job_handler.update_job(job_id, job_info)
                print(f"[{job_id}] [AZURE_TASKS] Tarefas criadas: {created_tasks}")
                print(f"[{job_id}] [DEBUG] Atualizando status do job para 'completed' após criação de tarefas Azure.")
                self.job_handler.update_job_status(job_id, 'completed')
                print(f"[{job_id}] [DEBUG] Workflow finalizado após criação de tarefas Azure.")
                return
            # ==================================================================
            # == FIM DA MUDANÇA 1 ==
            # ==================================================================

            if start_from_step > 0 and analysis_type == 'criacao_epicos_azure_devops':
                print(f"[{job_id}] [DEBUG] Chamando AzureBoardService.create_epics: agente={analysis_type}")
                organization = job_info['data'].get('organization') or job_info['data'].get('azure_organization')
                project = job_info['data'].get('project') or job_info['data'].get('azure_project')
                report = job_info['data'].get('analysis_report')
                azure_board_service = AzureBoardService(organization, project, self.secret_manager)
                created_epics = azure_board_service.create_epics(report)
                print(f"[{job_id}] [DEBUG] Resultado AzureBoardService.create_epics: {created_epics}")
                job_info['data']['epicos_criados'] = created_epics
                self.job_handler.update_job(job_id, job_info)
                print(f"[{job_id}] [AZURE_EPICS] Épicos criados: {created_epics}")
                self.job_handler.update_job_status(job_id, 'completed')
                print(f"[{job_id}] [DEBUG] Workflow finalizado após criação de épicos Azure.")
                return
                
            if analysis_type == 'revisor_tarefas' and start_from_step > 0:
                task_id = job_info['data'].get('task_id')
                report = job_info['data'].get('analysis_report')
                organization = job_info['data'].get('organization') or job_info['data'].get('azure_organization')
                project = job_info['data'].get('project') or job_info['data'].get('azure_project')
                azure_board_service = AzureBoardService(organization, project, self.secret_manager)
                task_discussion_updater_service = TaskDiscussionUpdaterService()
                print(f"[{job_id}] [DEBUG][DISCUSSION] Antes de update_task_from_report: task_id={task_id}, tamanho_report={len(report) if report else 0}, report_preview={str(report)[:200] if report else ''}")
                update_result = task_discussion_updater_service.update_task_from_report(task_id, report, azure_board_service)
                print(f"[{job_id}] [DEBUG][DISCUSSION] Depois de update_task_from_report: update_result={update_result}")
                job_info['data']['task_discussion_update_result'] = update_result
                self.job_handler.update_job(job_id, job_info)
                if update_result.get('error') or (not update_result.get('success', True)):
                    print(f"[{job_id}] [ERROR][DISCUSSION] Falha ao atualizar discussion da task: {update_result}")
                    self.job_handler.update_job_status(job_id, 'failed')
                    return
                print(f"[{job_id}] [DEBUG][DISCUSSION] Discussion da task atualizada com sucesso: {update_result}")
                self.job_handler.update_job_status(job_id, 'completed')
                return
                
            if start_from_step == 0:
                print(f"[{job_id}] [DEBUG] Entrando no step 0. analysis_type={analysis_type}")
                if analysis_type == 'revisor_tarefas':
                    print(f"[{job_id}] [DEBUG] Step 0 (revisor_tarefas): task_id={job_info['data'].get('task_id')}, epic_id={job_info['data'].get('epic_id')}, status_update={workflow.get('steps', [])[0].get('status_update')}")
                report_from_blob = self.report_handler.blob_storage.read_report(
                    projeto=projeto,
                    analysis_type=analysis_type,
                    repository_type=repository_type,
                    repo_name=repo_name,
                    branch_name=branch_name,
                    analysis_name=analysis_name
                )
                if report_from_blob is not None and report_from_blob.strip():
                    job_info['data']['analysis_report'] = report_from_blob
                    report_blob_url = self.report_handler.blob_storage.get_report_url(
                        projeto=projeto,
                        analysis_type=analysis_type,
                        repository_type=repository_type,
                        repo_name=repo_name,
                        branch_name=branch_name,
                        analysis_name=analysis_name
                    )
                    job_info['data']['report_blob_url'] = report_blob_url
                    self.job_handler.update_job(job_id, job_info)
                    print(f"[{job_id}] [DEBUG] Relatório encontrado no Blob Storage. Workflow pausado para aprovação.")
                    self.handle_approval_step(job_id, job_info, 0, {'relatorio': report_from_blob})
                    return
                else:
                    print(f"[{job_id}] [DEBUG] Relatório NÃO encontrado no Blob Storage. Prosseguindo para geração.")
                    
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
                    if current_step_index == 0 and analysis_type == 'revisor_tarefas':
                        print(f"[{job_id}] [DEBUG] Executando step 0 com task_id={job_info['data'].get('task_id')}, epic_id={job_info['data'].get('epic_id')}, status_update={step.get('status_update')} (revisor_tarefas)")
                    
                    print(f"[{job_id}] [DEBUG] Antes de chamar _execute_step_with_strategy para step {current_step_index} (analysis_type={analysis_type})")
                    step_result = self._execute_step_with_strategy(
                        job_id, job_info, step, current_step_index, previous_step_result, repo_reader, i, start_from_step
                    )
                    print(f"[{job_id}] [DEBUG] Depois de _execute_step_with_strategy para step {current_step_index} (analysis_type={analysis_type}), resultado: {str(step_result)[:300]}...")
                    
                    if current_step_index == 0:
                        print(f"[{job_id}] [DEBUG] Step 0: resultado do agente: {str(step_result)[:300]}...")
                        if analysis_type == 'revisor_tarefas':
                            print(f"[{job_id}] [DEBUG] Step 0: análise revisor_tarefas, chamando _save_generated_report explicitamente.")
                            report_saved = self._save_generated_report(job_id, job_info, step_result, current_step_index)
                            print(f"[{job_id}] [DEBUG] Step 0: _save_generated_report retornou {report_saved}")
                            if not report_saved:
                                print(f"[{job_id}] [ERRO] Relatório não foi salvo no step 0 (revisor_tarefas). Lançando exceção.")
                                raise ValueError(f"[{job_id}] ERRO: Relatório não foi salvo no step 0 para analysis_type='revisor_tarefas'.")
                            if step.get('requires_approval', False):
                                print(f"[{job_id}] [DEBUG] Step 0: requires_approval=True, chamando handle_approval_step")
                                self.handle_approval_step(job_id, job_info, current_step_index, step_result)
                                return
                        else:
                            report_text = self.report_handler.extract_report_text(step_result)
                            if report_text and report_text.strip():
                                print(f"[{job_id}] [DEBUG] Step 0: relatório gerado, salvando...")
                                self._save_generated_report(job_id, job_info, step_result, current_step_index)
                                if step.get('requires_approval', False):
                                    print(f"[{job_id}] [DEBUG] Step 0: requires_approval=True, chamando handle_approval_step")
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
                # ... (Lógica de finalização _finalize_workflow) ...
                self._finalize_workflow(job_id, job_info, workflow, previous_step_result, repository_type, repo_name)

        except Exception as e:
            error_message = str(e)
            print(f"[{job_id}] ERRO FATAL NO WORKFLOW: {error_message}")
            traceback.print_exc()
            
            # Atualiza os dados do job com o erro antes de mudar o status
            try:
                # job_info deve estar acessível neste escopo
                if job_info and 'data' in job_info:
                    job_info['data']['error_details'] = error_message
                    self.job_handler.update_job(job_id, job_info)
            except Exception as update_err:
                print(f"[{job_id}] ERRO CRÍTICO: Falha ao salvar detalhes do erro no job: {update_err}")

            # Agora atualiza o status SEM o argumento de erro
            self.job_handler.update_job_status(job_id, 'failed')
    
    def _execute_step_with_strategy(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], 
                                    current_step_index: int, previous_step_result: Dict[str, Any], 
                                    repo_reader: ReaderGeral, step_iteration: int, 
                                    start_from_step: int, batch_steps: Optional[list] = None, 
                                    agent_params_override: Optional[dict] = None) -> Dict[str, Any]:
        
        model_para_etapa = step.get('model_name', job_info.get('data', {}).get('model_name'))
        llm_provider = LLMProviderFactory.create_provider(model_para_etapa, self.rag_retriever)
        agent_params = step.get('params', {}).copy() if step.get('params') else {}
        agent_type = step.get('agent_type', step.get('agent'))
        analysis_type = job_info['data'].get('original_analysis_type')
        agent_params['instrucoes_extras'] = job_info['data'].get('instrucoes_extras', '')
        agent_params['tipo_analise'] = analysis_type

        if agent_type == 'revisor_board':
            epic_id = job_info['data'].get('epic_id') or job_info['data'].get('epic_id')
            organization = job_info['data'].get('organization') or job_info['data'].get('azure_organization')
            project = job_info['data'].get('project') or job_info['data'].get('azure_project')
            
            agent_params['epic_id'] = epic_id
            agent_params['organization'] = organization
            agent_params['project'] = project
            agent_params['task_id'] = job_info['data'].get('task_id')
            
            # Adiciona o feature_id para todos os fluxos do revisor_board
            agent_params['feature_id'] = job_info['data'].get('feature_id')
            
            if analysis_type == 'revisor_tarefas':
                print(f"[{job_id}] [DEBUG] _execute_step_with_strategy: analysis_type=revisor_tarefas, task_id propagado: {agent_params['task_id']}")
            elif analysis_type == 'criacao_features_azure_devops': # Este é o 'tipo_analise' do *agente* que gera tarefas
                print(f"[{job_id}] [DEBUG] _execute_step_with_strategy: analysis_type={analysis_type}, feature_id propagado: {agent_params['feature_id']}")

        elif agent_type == 'comparador':
            agent_params.update({
                'repo_name_modernizado': job_info['data'].get('repo_name_modernizado'),
                'branch_name_modernizado': job_info['data'].get('branch_name_modernizado'),
                'repo_name_original': job_info['data'].get('repo_name_original'),
                'branch_name_original': job_info['data'].get('branch_name_original')
            })
        else:
            repo_name = job_info['data'].get('repo_name_modernizado')
            if analysis_type not in ['criacao_epicos_azure_devops', 'criacao_tarefas_azure_devops', 'revisor_tarefas', 'criacao_features_azure_devops']:
                branch_name = job_info['data'].get('branch_name_modernizado')
                if branch_name:
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
            
        if agent_type == 'revisor_board':
            print(f"[{job_id}] [DEBUG] _execute_step_with_strategy: Antes de chamar AgentFactory, agent_type=revisor_board, epic_id={agent_params.get('epic_id')}, feature_id={agent_params.get('feature_id')}, task_id={agent_params.get('task_id')}")
            
        strategy = StepStrategyFactory.create_strategy(step, self.job_handler)
        print(f"[{job_id}] [DEBUG] Chamando strategy.execute_step para agent_type={agent_type}, step={current_step_index}")
        
        result = strategy.execute_step(
            job_id, job_info, step, current_step_index, 
            previous_step_result, repo_reader, llm_provider, agent_params
        )
        
        print(f"[{job_id}] [DEBUG] strategy.execute_step retornou resultado para step {current_step_index}: {str(result)[:300]}...")
        
        if current_step_index == 0:
            print(f"[{job_id}] [DEBUG] Salvando relatório gerado pelo agente no step 0.")
            report_text = self.report_handler.extract_report_text(result)
            print(f"[{job_id}] [DEBUG] extract_report_text retornou: {str(report_text)[:200]}...")
            if report_text and report_text.strip():
                self._save_generated_report(job_id, job_info, result, current_step_index)
                print(f"[{job_id}] [DEBUG] Relatório salvo com sucesso no step {current_step_index}.")
                
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
        batch_results = job_info['data'].get(JobFields.BATCH_RESULTS, []) # Correção: Adicionar default
        if not batch_results:
            print(f"[{job_id}] [DEBUG] _finalize_workflow: Nenhum batch result encontrado, pulando finalização incremental.")
            self.job_handler.update_job_status(job_id, 'completed')
            return

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
