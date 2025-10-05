import json
from typing import Dict, Any, Optional
from models import JobFields

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
        job_info['data'][JobFields.ANALYSIS_REPORT] = report_text
        url = self.report_handler.save_report_to_blob(job_id, job_info, report_text, report_generated_by_agent=True)
        if not url:
            raise ValueError(f"[{job_id}] ERRO CRÍTICO: Relatório não foi salvo no Blob Storage")
        print(f"[{job_id}] Relatório salvo com sucesso: {url}")
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

            for i, step in enumerate(steps_to_run):
                current_step_index = start_from_step + i
                print(f"[{job_id}] Executando step {current_step_index}/{len(workflow.get('steps', []))-1}")
                print(f"[{job_id}] gerar_relatorio_apenas: {job_info.get('data', {}).get(JobFields.GERAR_RELATORIO_APENAS)}")

                print(f"[{job_id}] Status atual: {step['status_update']}")
                self.job_handler.update_job_status(job_id, step['status_update'])

                report_generated_by_agent = False

                if current_step_index == 0:
                    existing_report_result = self.report_handler.try_read_existing_report(job_id, job_info, current_step_index)
                    existing_report_text = self.report_handler.validate_and_parse_blob_report(existing_report_result, job_id)
                    if existing_report_text:
                        job_info['data'][JobFields.ANALYSIS_REPORT] = existing_report_text
                        report_data = {'relatorio': existing_report_text}
                        self.job_handler.save_step_result(job_info, current_step_index, report_data)
                        strategy = StepStrategyFactory.create_strategy(step, self.job_handler)
                        if strategy.should_finalize_workflow(job_info, current_step_index):
                            print(f"[{job_id}] Workflow finalizado no step {current_step_index}")
                            print(f"[{job_id}] Relatório disponível: {bool(job_info['data'].get(JobFields.ANALYSIS_REPORT))}")
                            print(f"[{job_id}] Blob URL: {job_info['data'].get(JobFields.REPORT_BLOB_URL)}")
                            self.job_handler.update_job_status(job_id, 'completed')
                            print(f"[{job_id}] Workflow finalizado com sucesso (modo report_only)")
                            return
                        if strategy.should_pause_for_approval(step):
                            self.handle_approval_step(job_id, job_info, current_step_index, report_data)
                            return
                        previous_step_result = report_data
                        continue
                    else:
                        print(f"[{job_id}] Relatório inválido ou vazio lido do Blob. Gerando novo relatório.")
                        report_generated_by_agent = True

                step_result = self._execute_step_with_strategy(job_id, job_info, step, current_step_index, 
                                                             previous_step_result, repo_reader, i, start_from_step)
                self.job_handler.save_step_result(job_info, current_step_index, step_result)
                previous_step_result = step_result

                if current_step_index == 0 and report_generated_by_agent:
                    print(f"[{job_id}] Salvando relatório gerado pelo agente no Blob Storage (step 0)")
                    sucesso_salvar = self._save_generated_report(job_id, job_info, step_result, current_step_index)
                    if not sucesso_salvar:
                        raise ValueError(f"[{job_id}] ERRO: Relatório gerado pelo agente está vazio e não pode ser salvo.")
                    if not job_info['data'].get(JobFields.REPORT_BLOB_URL):
                        raise ValueError(f"[{job_id}] ERRO CRÍTICO: Relatório não foi salvo no Blob Storage")
                    print(f"[{job_id}] Relatório salvo com sucesso: {job_info['data'][JobFields.REPORT_BLOB_URL]}")

                strategy = StepStrategyFactory.create_strategy(step, self.job_handler)

                if strategy.should_finalize_workflow(job_info, current_step_index):
                    print(f"[{job_id}] Workflow finalizado no step {current_step_index}")
                    print(f"[{job_id}] Relatório disponível: {bool(job_info['data'].get(JobFields.ANALYSIS_REPORT))}")
                    print(f"[{job_id}] Blob URL: {job_info['data'].get(JobFields.REPORT_BLOB_URL)}")
                    self.job_handler.update_job_status(job_id, 'completed')
                    print(f"[{job_id}] Workflow finalizado com sucesso (modo report_only)")
                    return

                if strategy.should_pause_for_approval(step):
                    self.handle_approval_step(job_id, job_info, current_step_index, step_result)
                    return

            self._finalize_workflow(job_id, job_info, workflow, previous_step_result, repository_type, repo_name)

        except Exception as e:
            self.job_handler.handle_job_error(job_id, e, 'workflow')

    def _execute_step_with_strategy(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], 
                                   current_step_index: int, previous_step_result: Dict[str, Any], 
                                   repo_reader: ReaderGeral, step_iteration: int, start_from_step: int) -> Dict[str, Any]:

        model_para_etapa = step.get('model_name', job_info.get('data', {}).get('model_name'))
        llm_provider = LLMProviderFactory.create_provider(model_para_etapa, self.rag_retriever)
        agent_params = step.get('params', {}).copy()

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

        retornar_lista_arquivos = job_info.get('data', {}).get(JobFields.RETORNAR_LISTA_ARQUIVOS, False)
        print(f"[{job_id}] Flag retornar_lista_arquivos: {retornar_lista_arquivos}")

        agent_params.update({
            'usar_rag': job_info.get("data", {}).get("usar_rag", False), 
            'model_name': model_para_etapa,
            'repository_type': job_info['data']['repository_type'],
            'retornar_lista_arquivos': retornar_lista_arquivos,
            'modo_adicao_incremental': job_info.get('data', {}).get(JobFields.MODO_ADICAO_INCREMENTAL, False),
            'usuario_executor': job_info.get('data', {}).get(JobFields.USUARIO_EXECUTOR)
        })

        strategy = StepStrategyFactory.create_strategy(step, self.job_handler)

        return strategy.execute_step(
            job_id, job_info, step, current_step_index, 
            previous_step_result, repo_reader, llm_provider, agent_params
        )

    def handle_approval_step(self, job_id: str, job_info: Dict[str, Any], step_index: int, step_result: Dict[str, Any]) -> None:
        print(f"[{job_id}] Etapa requer aprovação.")
        report_text = self.report_handler.extract_report_text(step_result)
        job_info['data'][JobFields.ANALYSIS_REPORT] = report_text
        job_info['status'] = 'pending_approval'
        self.job_handler.set_paused_step(job_info, step_index)
        self.job_handler.update_job(job_id, job_info)

    def _finalize_workflow(self, job_id: str, job_info: Dict[str, Any], workflow: Dict[str, Any], 
                          final_result: Dict[str, Any], repository_type: str, repo_name: str) -> None:

        resultado_agrupamento, resultado_refatoracao = self.data_formatter.extract_workflow_results(
            job_info, workflow, final_result
        )

        job_info['data'][JobFields.DIAGNOSTIC_LOGS] = {
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

        print(f"[{job_id}] DIAGNÓSTICO - Atualizando job após commits com commit_details: {job_info['data'].get(JobFields.COMMIT_DETAILS, [])}")
        self.job_handler.update_job(job_id, job_info)
        print(f"[{job_id}] DIAGNÓSTICO - Job atualizado no job store")

        self.job_handler.update_job_status(job_id, 'completed')
