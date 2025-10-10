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

class WorkflowOrchestrator(IWorkflowOrchestrator):
    def __init__(self, job_manager: IJobManager, blob_storage: IBlobStorageService, 
                 workflow_registry: Dict[str, Any], rag_retriever=None, 
                 job_handler: JobHandler = None, report_handler: ReportHandler = None,
                 commit_handler: CommitHandler = None, data_formatter: DataFormatter = None):
        self.workflow_registry = workflow_registry
        self.rag_retriever = rag_retriever or AzureAISearchRAGRetriever()
        self.job_handler = job_handler or JobHandler(job_manager)
        self.report_handler = report_handler or ReportHandler(blob_storage)
        self.commit_handler = commit_handler or CommitHandler()
        self.data_formatter = data_formatter or DataFormatter()

    def _save_generated_report(self, job_id: str, job_info: Dict[str, Any], step_result: Dict[str, Any], current_step_index: int) -> bool:
        report_text = self.report_handler.extract_report_text(step_result)
        if not report_text or len(report_text.strip()) == 0:
            print(f"[{job_id}] ERRO: Relatório gerado pelo agente está vazio no step {current_step_index}.")
            return False
        print(f"[{job_id}] [DEBUG] Salvando relatório gerado pelo agente. gerar_relatorio_apenas: {job_info['data'].get(JobFields.GERAR_RELATORIO_APENAS)}, tamanho do relatório: {len(report_text)}")
        job_info['data']['analysis_report'] = report_text
        url = self.report_handler.save_report_to_blob(job_id, job_info, report_text, report_generated_by_agent=True)
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
            repository_type = job_info['data']['repository_type']
            repo_name = job_info['data']['repo_name']
            repository_provider = get_repository_provider_explicit(repository_type)
            repo_reader = ReaderGeral(repository_provider=repository_provider)
            previous_step_result = self.job_handler.get_step_result(job_info, start_from_step)
            steps_to_run = workflow.get('steps', [])[start_from_step:]
            executar_incremental = job_info['data'].get(JobFields.EXECUTAR_STEPS_INCREMENTALMENTE, False)

            # INICIO DA MODIFICACAO: Quebra do relatório em batches APÓS aprovação e ANTES da execução do step 1
            if executar_incremental and start_from_step >= 1:
                if JobFields.STEP_BATCHES not in job_info['data'] or not job_info['data'][JobFields.STEP_BATCHES]:
                    report_text = job_info['data'].get('analysis_report')
                    if not report_text:
                        raise ValueError(f"[{job_id}] ERRO: Não há relatório aprovado para parsing incremental.")
                    step_batches = IncrementalStepExecutorService.get_step_batches_from_report(report_text)
                    job_info['data'][JobFields.STEP_BATCHES] = step_batches
                    job_info['data'][JobFields.CURRENT_BATCH_INDEX] = 0
                    job_info['data'][JobFields.BATCH_RESULTS] = []
                    self.job_handler.update_job(job_id, job_info)
                    print(f"[{job_id}] [INCREMENTAL] step_batches inicializados com {len(step_batches)} batches.")
            # FIM DA MODIFICACAO

            # Step 0: geração do relatório
            for i, step in enumerate(steps_to_run):
                current_step_index = start_from_step + i
                print(f"[{job_id}] Executando step {current_step_index}/{len(workflow.get('steps', []))-1}")
                print(f"[{job_id}] gerar_relatorio_apenas: {job_info.get('data', {}).get(JobFields.GERAR_RELATORIO_APENAS)}")
                print(f"[{job_id}] Status atual: {step['status_update']}")
                self.job_handler.update_job_status(job_id, step['status_update'])

                # INCREMENTAL EXECUTION LOGIC FOR STEP 1 (APLICAÇÃO DE MUDANÇAS)
                if executar_incremental and current_step_index == 1:
                    step_batches = job_info['data'][JobFields.STEP_BATCHES]
                    current_batch_index = job_info['data'].get(JobFields.CURRENT_BATCH_INDEX, 0)
                    batch_results = job_info['data'].get(JobFields.BATCH_RESULTS, [])
                    total_batches = len(step_batches)
                    for batch_idx in range(current_batch_index, total_batches):
                        batch = step_batches[batch_idx]
                        print(f"[{job_id}] [INCREMENTAL] Processando batch {batch_idx+1}/{total_batches} com {len(batch)} steps.")
                        agent_params = step.get('params', {}).copy() if step.get('params') else {}
                        agent_params['current_batch'] = batch
                        agent_params['batch_index'] = batch_idx
                        agent_params['total_batches'] = total_batches
                        result = self._execute_step_with_strategy(
                            job_id, job_info, step, current_step_index, previous_step_result, repo_reader, i, start_from_step, batch_steps=batch, agent_params_override=agent_params
                        )
                        print(f"[{job_id}] [INCREMENTAL] Batch {batch_idx+1}/{total_batches} executado. Tamanho do resultado: {len(str(result)) if result is not None else 0}")
                        batch_results.append(result)
                        job_info['data'][JobFields.BATCH_RESULTS] = batch_results
                        job_info['data'][JobFields.CURRENT_BATCH_INDEX] = batch_idx + 1
                        self.job_handler.update_job(job_id, job_info)
                    print(f"[{job_id}] [INCREMENTAL] Todos os batches ({total_batches}) processados.")
                    previous_step_result = {'incremental_results': batch_results}
                    print(f"[{job_id}] [INCREMENTAL] Resultados dos batches consolidados para o próximo step.")
                    continue  # Não executa o step padrão, já processou incrementalmente

                # Execução padrão para outros steps
                step_result = self._execute_step_with_strategy(
                    job_id, job_info, step, current_step_index, previous_step_result, repo_reader, i, start_from_step
                )
                self.job_handler.save_step_result(job_info, current_step_index, step_result)
                previous_step_result = step_result
                strategy = StepStrategyFactory.create_strategy(step, self.job_handler)
                if strategy.should_finalize_workflow(job_info, current_step_index):
                    print(f"[{job_id}] Workflow finalizado no step {current_step_index} (gerar_relatorio_apenas=True)")
                    print(f"[{job_id}] Relatório disponível: {bool(job_info['data'].get('analysis_report'))}")
                    print(f"[{job_id}] Blob URL: {job_info['data'].get('report_blob_url')}")
                    print(f"[{job_id}] [execute_workflow] (ANTES update_job_status completed) gerar_relatorio_apenas: {job_info['data'].get(JobFields.GERAR_RELATORIO_APENAS)}, tamanho analysis_report: {len(job_info['data'].get('analysis_report', ''))}, report_blob_url: {job_info['data'].get('report_blob_url')}")
                    analysis_report = job_info['data'].get('analysis_report')
                    if job_info['data'].get(JobFields.GERAR_RELATORIO_APENAS) is True:
                        if not analysis_report or len(analysis_report.strip()) < 100:
                            raise ValueError(f"[{job_id}] ERRO CRÍTICO: Tentativa de finalizar workflow no modo report_only sem relatório válido. analysis_report={'presente' if analysis_report else 'ausente'}, tamanho={len(analysis_report) if analysis_report else 0}")
                    self.job_handler.update_job_status(job_id, 'completed')
                    print(f"[{job_id}] [execute_workflow] (DEPOIS update_job_status completed) gerar_relatorio_apenas: {job_info['data'].get(JobFields.GERAR_RELATORIO_APENAS)}, tamanho analysis_report: {len(job_info['data'].get('analysis_report', ''))}, report_blob_url: {job_info['data'].get('report_blob_url')}")
                    print(f"[{job_id}] Workflow finalizado com sucesso (modo report_only)")
                    return
                if strategy.should_pause_for_approval(job_info, step):
                    self.handle_approval_step(job_id, job_info, current_step_index, step_result)
                    return
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
            repo_name = job_info['data'].get('repo_name_modernizado', job_info['data']['repo_name'])
            branch_name = job_info['data'].get('branch_name_modernizado', job_info['data']['branch_name'])
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
        strategy = StepStrategyFactory.create_strategy(step, self.job_handler)
        return strategy.execute_step(
            job_id, job_info, step, current_step_index, 
            previous_step_result, repo_reader, llm_provider, agent_params
        )

    def handle_approval_step(self, job_id: str, job_info: Dict[str, Any], step_index: int, step_result: Dict[str, Any]) -> None:
        print(f"[{job_id}] Etapa requer aprovação.")
        report_text = self.report_handler.extract_report_text(step_result)
        job_info['data']['analysis_report'] = report_text
        job_info['status'] = 'pending_approval'
        self.job_handler.set_paused_step(job_info, step_index)
        self.job_handler.update_job(job_id, job_info)

    def _finalize_workflow(self, job_id: str, job_info: Dict[str, Any], workflow: Dict[str, Any], 
                          final_result: Dict[str, Any], repository_type: str, repo_name: str) -> None:
        executar_incremental = job_info['data'].get(JobFields.EXECUTAR_STEPS_INCREMENTALMENTE, False)
        if executar_incremental and JobFields.BATCH_RESULTS in job_info['data']:
            batch_results = job_info['data'][JobFields.BATCH_RESULTS]
            total_batches = len(batch_results)
            total_steps = sum(len(batch) if isinstance(batch, list) else 1 for batch in batch_results)
            print(f"[{job_id}] [INCREMENTAL] Finalizando workflow incremental. Batches processados: {total_batches}, Steps executados: {total_steps}.")
            final_result = {'incremental_results': batch_results}
        resultado_agrupamento, resultado_refatoracao = self.data_formatter.extract_workflow_results(
            job_info, workflow, final_result
        )
        job_info['data']['diagnostic_logs'] = {
            "penultimate_result": resultado_refatoracao,
            "final_result": resultado_agrupamento
        }
        self.job_handler.update_job_status(job_id, 'populating_data')
        dados_preenchidos = self.data_formatter.populate_changeset_data(
            resultado_agrupamento, resultado_refatoracao
        )
        dados_finais_formatados = self.data_formatter.format_final_data(dados_preenchidos)
        self.job_handler.update_job_status(job_id, 'committing_to_github')
        self.commit_handler.execute_commits(job_id, job_info, dados_finais_formatados, repository_type, repo_name)
        print(f"[{job_id}] DIAGNÓSTICO - Atualizando job após commits com commit_details: {job_info['data'].get('commit_details', [])}")
        self.job_handler.update_job(job_id, job_info)
        print(f"[{job_id}] DIAGNÓSTICO - Job atualizado no job store")
        self.job_handler.update_job_status(job_id, 'completed')
