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

    def _validate_report_artifacts(self, job_id: str, job_info: Dict[str, Any]):
        analysis_report = job_info['data'].get(JobFields.ANALYSIS_REPORT)
        blob_url = job_info['data'].get(JobFields.REPORT_BLOB_URL)
        if not analysis_report or not blob_url:
            raise ValueError(f"[{job_id}] ERRO: Tentativa de finalizar sem relatório completo. Blob URL: {blob_url}, Report exists: {bool(analysis_report)}")
        print(f"[{job_id}] [VALIDACAO] Artefatos de relatório validados com sucesso.")

    def _execute_and_finalize_step_zero(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], repo_reader, llm_provider, agent_params: Dict[str, Any]) -> Dict[str, Any]:
        gerar_novo = job_info['data'].get(JobFields.GERAR_NOVO_RELATORIO, True)
        report_only = job_info['data'].get(JobFields.GERAR_RELATORIO_APENAS, False)
        print(f"[{job_id}] [STEP_0] Iniciando - gerar_novo_relatorio={gerar_novo}, gerar_relatorio_apenas={report_only}")
        report_text = None
        step_result = None
        # 1. Tentar ler relatório existente (se permitido)
        if not gerar_novo:
            print(f"[{job_id}] [STEP_0] Tentando ler relatório existente do blob")
            existing_report = self.report_handler.try_read_existing_report(job_id, job_info, 0)
            report_text = self.report_handler.validate_and_parse_blob_report(existing_report, job_id, gerar_novo)
        # 2. Executar agente se necessário
        if not report_text:
            print(f"[{job_id}] [STEP_0] Executando agente para gerar relatório - Flags: gerar_relatorio_apenas={report_only}, gerar_novo_relatorio={gerar_novo}")
            strategy = StepStrategyFactory.create_strategy(step, self.job_handler)
            step_result = strategy.execute_step(
                job_id, job_info, step, 0, None, repo_reader, llm_provider, agent_params
            )
            report_text = self.report_handler.extract_report_text(step_result)
           # if not self.report_handler.is_valid_report(report_text):
            #    raise ValueError(f"[{job_id}] Agente não gerou relatório válido")
            report_source = 'agent'
        else:
            step_result = {'relatorio': report_text}
        # 3. Salvar relatório no job e blob
        job_info['data'][JobFields.ANALYSIS_REPORT] = report_text
        url = self.report_handler.save_report_to_blob(job_id, job_info, report_text)
        print(f"[{job_id}] [STEP_0] Relatório salvo: {url} - Flags: gerar_relatorio_apenas={report_only}, gerar_novo_relatorio={gerar_novo}")
        # 4. Validar artefatos
        self._validate_report_artifacts(job_id, job_info)
        # 5. Decidir se deve parar
        should_stop = report_only
        print(f"[{job_id}] [STEP_0] Decisão: should_stop={should_stop} - Flags: gerar_relatorio_apenas={report_only}, gerar_novo_relatorio={gerar_novo}")
        return {'should_stop': should_stop, 'step_result': step_result}

    def execute_workflow(self, job_id: str, start_from_step: int = 0) -> None:
        job_info = self.job_handler.get_job_info(job_id)
        gerar_relatorio_apenas = job_info.get('data', {}).get(JobFields.GERAR_RELATORIO_APENAS, False)
        gerar_novo_relatorio = job_info.get('data', {}).get(JobFields.GERAR_NOVO_RELATORIO, True)
        print(f"[{job_id}] [DECISAO] Iniciando workflow - Flags: gerar_relatorio_apenas={gerar_relatorio_apenas}, gerar_novo_relatorio={gerar_novo_relatorio}")
        workflow = self.workflow_registry.get(job_info['data']['original_analysis_type'])
        print(f"[{job_id}] Total de steps no workflow: {len(workflow.get('steps', []))}")
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
                print(f"[{job_id}] gerar_relatorio_apenas: {gerar_relatorio_apenas}, gerar_novo_relatorio: {gerar_novo_relatorio}")
                print(f"[{job_id}] Status atual: {step['status_update']}")
                self.job_handler.update_job_status(job_id, step['status_update'])
                if current_step_index == 0:
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
                        repo_name_modernizado = job_info['data'].get('repo_name_modernizado', job_info['data']['repo_name'])
                        branch_name_modernizado = job_info['data'].get('branch_name_modernizado', job_info['data']['branch_name'])
                        agent_params.update({
                            'repositorio': repo_name_modernizado,
                            'nome_branch': branch_name_modernizado
                        })
                    retornar_lista_arquivos = job_info.get('data', {}).get(JobFields.RETORNAR_LISTA_ARQUIVOS, False)
                    agent_params.update({
                        'usar_rag': job_info.get("data", {}).get("usar_rag", False), 
                        'model_name': model_para_etapa,
                        'repository_type': job_info['data']['repository_type'],
                        'retornar_lista_arquivos': retornar_lista_arquivos,
                        'modo_adicao_incremental': job_info.get('data', {}).get(JobFields.MODO_ADICAO_INCREMENTAL, False),
                        'usuario_executor': job_info.get('data', {}).get(JobFields.USUARIO_EXECUTOR)
                    })
                    result_step_zero = self._execute_and_finalize_step_zero(
                        job_id, job_info, step, repo_reader, llm_provider, agent_params
                    )
                    self.job_handler.save_step_result(job_info, current_step_index, result_step_zero['step_result'])
                    previous_step_result = result_step_zero['step_result']
                    if result_step_zero['requires_approval']:
                        self.handle_approval_step(job_id, job_info, current_step_index, result_step_zero['step_result'])
                        return
                    if result_step_zero['should_stop']:
                        self.job_handler.update_job_status(job_id, 'completed')
                        print(f"[{job_id}] [DECISAO] Workflow finalizado após step 0 - Flags: gerar_relatorio_apenas={gerar_relatorio_apenas}, gerar_novo_relatorio={gerar_novo_relatorio}")
                        return
                    continue
                strategy = StepStrategyFactory.create_strategy(step, self.job_handler)
                step_result = self._execute_step_with_strategy(job_id, job_info, step, current_step_index, 
                                                             previous_step_result, repo_reader, i, start_from_step)
                self.job_handler.save_step_result(job_info, current_step_index, step_result)
                previous_step_result = step_result
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
        self._validate_report_artifacts(job_id, job_info)
        self.job_handler.update_job_status(job_id, 'completed')
