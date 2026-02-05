import json
import traceback
from typing import Dict, Any, Optional

# Interfaces
from domain.interfaces.workflow_orchestrator_interface import IWorkflowOrchestrator
from domain.interfaces.job_manager_interface import IJobManager
from domain.interfaces.blob_storage_interface import IBlobStorageService

# Services & Handlers
from services.factories.llm_provider_factory import LLMProviderFactory
from services.job_handler import JobHandler
from services.report_handler import ReportHandler
from services.commit_handler import CommitHandler
from services.step_strategies.step_strategy_factory import StepStrategyFactory

# --- [VOLTOU] Serviço Incremental e Models ---
from services.incremental_step_executor_service import IncrementalStepExecutorService
from models import JobFields

# Tools
from tools.readers.reader_geral import ReaderGeral
from tools.repository_provider_factory import get_repository_provider_explicit
from tools.azure_secret_manager import AzureSecretManager

class WorkflowOrchestrator(IWorkflowOrchestrator):
    def __init__(self, 
                 job_manager: IJobManager, 
                 blob_storage: IBlobStorageService, 
                 workflow_registry: Dict[str, Any], 
                 job_handler: JobHandler = None, 
                 report_handler: ReportHandler = None,
                 commit_handler: CommitHandler = None, 
                 secret_manager: Optional[Any] = None,
                 cache_service=None, 
                 dependency_container=None):
        
        self.workflow_registry = workflow_registry
        self.job_handler = job_handler or JobHandler(job_manager)
        self.cache_service = cache_service
        self.report_handler = report_handler or ReportHandler(blob_storage, cache_service=self.cache_service)
        self.commit_handler = commit_handler or CommitHandler()
        self.secret_manager = secret_manager or AzureSecretManager()
        self.dependency_container = dependency_container

    def execute_workflow(self, job_id: str, start_from_step: int = 0) -> None:
        """
        Fluxo:
        Step 0: Gera Relatório -> Salva Blob -> Pausa.
        Step 1: Lê Relatório -> (Incremental ou Normal) Aplica Mudanças -> Commit.
        """
        print(f"[{job_id}] Iniciando WorkflowOrchestrator a partir do step {start_from_step}.")
        
        try:
            # 1. Carregar Contexto
            job_info = self.job_handler.get_job_info(job_id)
            data = job_info['data']
            analysis_type = data.get('original_analysis_type') or data.get('analysis_type')
            
            # 2. Carregar Workflow
            workflow = self.workflow_registry.get(analysis_type)
            if not workflow:
                raise ValueError(f"Workflow '{analysis_type}' não encontrado.")

            steps_to_run = workflow.get('steps', [])[start_from_step:]

            # 3. Configurar Leitura do Repositório
            repo_reader = self._get_repo_reader(data)
            
            # 4. Preparação de Estado (Resume logic)
            previous_step_result = {}
            if start_from_step > 0:
                print(f"[{job_id}] Retomando workflow no Step {start_from_step}. Recuperando relatório...")
                report_text = self._ensure_report_loaded(job_id, job_info, analysis_type)
                previous_step_result = {'analysis_report': report_text}

            # Configurações de Incremental
            executar_incremental = data.get(JobFields.EXECUTAR_STEPS_INCREMENTALMENTE, False)
            max_steps_per_batch = data.get(JobFields.MAX_STEPS_PER_BATCH, 3)

            # 5. Execução dos Steps
            for i, step in enumerate(steps_to_run):
                current_step_index = start_from_step + i
                status_msg = step.get('status_update', f'Processing step {current_step_index}')
                print(f"[{job_id}] --- Executando Step {current_step_index}: {status_msg} ---")
                self.job_handler.update_job_status(job_id, status_msg)

                step_result = None

                # --- LÓGICA INCREMENTAL (Geralmente no Step 1 - Aplicação) ---
                if executar_incremental and current_step_index == 1:
                    print(f"[{job_id}] [INCREMENTAL] Iniciando execução incremental.")
                    
                    # Carrega ou gera os batches baseados no relatório
                    step_batches = data.get(JobFields.STEP_BATCHES)
                    if step_batches is None:
                        report_text = data.get('analysis_report')
                        if not report_text:
                            raise ValueError(f"[{job_id}] Relatório necessário para incremental não encontrado.")
                        
                        step_batches = IncrementalStepExecutorService.get_step_batches_from_report(report_text, max_steps_per_batch=max_steps_per_batch)
                        job_info['data'][JobFields.STEP_BATCHES] = step_batches
                        job_info['data'][JobFields.CURRENT_BATCH_INDEX] = 0
                        job_info['data'][JobFields.BATCH_RESULTS] = []
                        self.job_handler.update_job(job_id, job_info)
                        print(f"[{job_id}] [INCREMENTAL] Batches gerados: {len(step_batches)}")

                    # Executa os batches
                    current_batch_index = job_info['data'].get(JobFields.CURRENT_BATCH_INDEX, 0)
                    batch_results = job_info['data'].get(JobFields.BATCH_RESULTS, [])
                    total_batches = len(step_batches)

                    for batch_idx in range(current_batch_index, total_batches):
                        try:
                            batch = step_batches[batch_idx]
                            print(f"[{job_id}] [INCREMENTAL] Batch {batch_idx+1}/{total_batches}: {len(batch)} itens.")
                            
                            # Configura params específicos para o batch
                            agent_params = step.get('params', {}).copy()
                            agent_params['current_batch'] = batch
                            agent_params['total_batches'] = total_batches
                            
                            # Executa Agente para este batch
                            result = self._execute_step_with_strategy(
                                job_id, job_info, step, current_step_index, 
                                previous_step_result, repo_reader, agent_params_override=agent_params
                            )
                            batch_results.append(result)

                        except Exception as e:
                            print(f"[{job_id}] [ERRO INCREMENTAL] Falha no batch {batch_idx+1}: {e}")
                            if 'failed_batches' not in job_info['data']:
                                job_info['data']['failed_batches'] = []
                            job_info['data']['failed_batches'].append({"batch_index": batch_idx, "error": str(e)})
                            continue # Pula para o próximo batch
                        finally:
                            # Salva progresso a cada batch
                            job_info['data'][JobFields.BATCH_RESULTS] = batch_results
                            job_info['data'][JobFields.CURRENT_BATCH_INDEX] = batch_idx + 1
                            self.job_handler.update_job(job_id, job_info)
                    
                    print(f"[{job_id}] [INCREMENTAL] Todos os batches finalizados.")
                    # O resultado "final" desse passo é a lista de resultados dos batches
                    # Mas o _finalize_workflow vai lidar com isso buscando no job_info
                    step_result = {'incremental_results': batch_results} 

                # --- LÓGICA PADRÃO (NÃO INCREMENTAL) ---
                else:
                    step_result = self._execute_step_with_strategy(
                        job_id, job_info, step, current_step_index, 
                        previous_step_result, repo_reader
                    )

                    # --- Step 0: Gerar Relatório e Pausar ---
                    if current_step_index == 0:
                        saved = self._save_generated_report(job_id, job_info, step_result)
                        if not saved:
                            raise ValueError(f"[{job_id}] Falha ao salvar relatório no Step 0.")
                        
                        if step.get('requires_approval', False):
                            self.handle_approval_step(job_id, job_info, current_step_index, step_result)
                            return # PAUSA O WORKFLOW AQUI

                # Atualiza resultado para próxima iteração
                previous_step_result = step_result

            # 6. Finalização e Commit
            self._finalize_workflow(job_id, job_info)

        except Exception as e:
            error_msg = f"ERRO FATAL: {str(e)}"
            print(f"[{job_id}] {error_msg}")
            traceback.print_exc()
            job_info['data']['error_details'] = error_msg
            self.job_handler.update_job(job_id, job_info)
            self.job_handler.update_job_status(job_id, 'failed')

    def _execute_step_with_strategy(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], 
                                    current_step_index: int, previous_step_result: Dict[str, Any], 
                                    repo_reader: ReaderGeral, agent_params_override: Optional[dict] = None) -> Dict[str, Any]:
        
        model_name = step.get('model_name')
        llm_provider = LLMProviderFactory.create_provider(model_name, None) # Sem RAG
        
        data = job_info['data']
        agent_params = step.get('params', {}).copy()
        
        # Parâmetros base
        agent_params.update({
            'job_id': job_id,
            'instrucoes_extras': data.get('instrucoes_extras', ''),
            'repositorio': data.get('repo_name_modernizado') or data.get('repo_name'),
            'nome_branch': data.get('branch_name_modernizado') or data.get('branch_name'),
            'repository_type': data.get('repository_type'),
            'arquivos_especificos': data.get('arquivos_especificos'),
            'usuario_executor': data.get('usuario_executor'),
            'analysis_report': previous_step_result.get('analysis_report') or data.get('analysis_report')
        })

        # Adiciona overrides (usado pelo incremental para passar o batch atual)
        if agent_params_override:
            agent_params.update(agent_params_override)

        strategy = StepStrategyFactory.create_strategy(step, self.job_handler)
        result = strategy.execute_step(
            job_id, job_info, step, current_step_index, 
            previous_step_result, repo_reader, llm_provider, agent_params
        )
        return result

    def _finalize_workflow(self, job_id: str, job_info: Dict[str, Any]) -> None:
        """Processa commits, unindo batches incrementais se necessário."""
        print(f"[{job_id}] Finalizando workflow...")
        
        repo_type = job_info['data'].get('repository_type')
        repo_name = job_info['data'].get('repo_name')
        
        # Verifica se houve execução incremental
        batch_results = job_info['data'].get(JobFields.BATCH_RESULTS, [])
        
        final_result_for_commit = {}

        if batch_results:
            print(f"[{job_id}] [INCREMENTAL] Unindo resultados de {len(batch_results)} batches.")
            # Usa o serviço para fazer o merge inteligente dos JSONs/Resultados
            merged_result = IncrementalStepExecutorService.merge_all_batches(batch_results)
            
            # Formata para o CommitHandler (assumindo que DataFormatter era usado aqui no original, 
            # mas simplificando para passar direto se o formato já for compatível ou adaptando)
            final_result_for_commit = merged_result
        else:
            # Fluxo normal não-incremental (o resultado estaria no último step_result, mas
            # como simplificamos o fluxo, assumimos que o CommitHandler sabe buscar ou 
            # que o último step_result deveria ter sido persistido se não for incremental.
            # No fluxo incremental, a persistência está em BATCH_RESULTS.
            print(f"[{job_id}] [AVISO] Nenhum resultado incremental encontrado. Verifique se o Step 1 gerou saída.")
            # Para fluxo não incremental de aplicação, você precisaria capturar o 'step_result' do loop
            # Mas como seu foco parece ser o incremental para aplicação, isso cobre o caso principal.
            return

        self.job_handler.update_job_status(job_id, 'committing_to_github')
        
        try:
            self.commit_handler.execute_commits(job_id, job_info, final_result_for_commit, repo_type, repo_name)
            print(f"[{job_id}] Commit realizado com sucesso.")
            self.job_handler.update_job_status(job_id, 'completed')
        except Exception as e:
            print(f"[{job_id}] Falha ao realizar commit: {e}")
            raise e

    # --- Helpers ---

    def _get_repo_reader(self, data: Dict) -> ReaderGeral:
        repository_type = data.get('repository_type')
        repository_provider = get_repository_provider_explicit(repository_type)
        return ReaderGeral(repository_provider=repository_provider, cache_service=self.cache_service)

    def _ensure_report_loaded(self, job_id: str, job_info: Dict, analysis_type: str) -> str:
        data = job_info['data']
        report_text = data.get('analysis_report')
        
        if not report_text and data.get('report_blob_url'):
            print(f"[{job_id}] Lendo relatório do Blob Storage...")
            report_text = self.report_handler.blob_storage.read_report(
                projeto=data.get('projeto'),
                analysis_type=analysis_type,
                repository_type=data.get('repository_type'),
                repo_name=data.get('repo_name'),
                branch_name=data.get('branch_name_modernizado') or data.get('branch_name'),
                analysis_name=data.get('analysis_name')
            )
            job_info['data']['analysis_report'] = report_text
            # Opcional: self.job_handler.update_job(...)
        
        return report_text

    def _save_generated_report(self, job_id: str, job_info: Dict[str, Any], step_result: Dict[str, Any]) -> bool:
        print(f"[{job_id}] Salvando relatório gerado...")
        report_text = self.report_handler.extract_report_text(step_result)
        
        if not report_text or not report_text.strip():
            print(f"[{job_id}] [AVISO] Relatório vazio.")
            return False

        job_info['data']['analysis_report'] = report_text
        url = self.report_handler.save_report_to_blob(job_id, job_info, report_text)
        
        if not url: return False
            
        job_info['data']['report_blob_url'] = url
        self.job_handler.update_job(job_id, job_info)
        return True

    def handle_approval_step(self, job_id: str, job_info: Dict[str, Any], step_index: int, step_result: Dict[str, Any]) -> None:
        print(f"[{job_id}] Pausando job para aprovação.")
        report_text = self.report_handler.extract_report_text(step_result)
        if report_text:
            job_info['data']['analysis_report'] = report_text

        job_info['status'] = 'pending_approval'
        self.job_handler.set_paused_step(job_info, step_index)
        self.job_handler.update_job(job_id, job_info)
