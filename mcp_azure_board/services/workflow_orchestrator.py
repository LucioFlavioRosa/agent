import json
import time
from typing import Dict, Any, Optional
from domain.interfaces.workflow_orchestrator_interface import IWorkflowOrchestrator
from domain.interfaces.job_manager_interface import IJobManager
from domain.interfaces.blob_storage_interface import IBlobStorageService
from services.report_handler import ReportHandler
from services.step_strategies.step_strategy_factory import StepStrategyFactory
import traceback

class WorkflowOrchestrator(IWorkflowOrchestrator):
    def __init__(self, job_manager: IJobManager, blob_storage: IBlobStorageService, 
                 workflow_registry: Dict[str, Any], rag_retriever=None, 
                 job_handler=None, report_handler=None,
                 secret_manager: Optional[Any] = None,
                 cache_service=None, dependency_container=None, azure_board_service=None):
        self.workflow_registry = workflow_registry
        self.rag_retriever = rag_retriever
        self.job_handler = job_handler
        self.cache_service = cache_service
        self.report_handler = report_handler or ReportHandler(blob_storage, cache_service=self.cache_service)
        self.secret_manager = secret_manager
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
        analysis_type = job_info['data'].get('original_analysis_type', '')
        workflow = self.workflow_registry.get(job_info['data']['original_analysis_type'])
        if not workflow:
            raise ValueError("Workflow não encontrado.")
        try:
            analysis_name = job_info['data'].get('analysis_name')
            projeto = job_info['data'].get('projeto')
            repository_type = job_info['data'].get('repository_type')
            repo_name = job_info['data'].get('repo_name')
            branch_name = job_info['data'].get('branch_name_modernizado')
            if start_from_step == 0:
                print(f"[{job_id}] [DEBUG] Entrando no step 0. analysis_type={analysis_type}")
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
            previous_step_result = self.job_handler.get_step_result(job_info, start_from_step)
            steps_to_run = workflow.get('steps', [])[start_from_step:]
            gerar_relatorio_apenas = job_info['data'].get('gerar_relatorio_apenas', False)
            for i, step in enumerate(steps_to_run):
                current_step_index = start_from_step + i
                print(f"[{job_id}] Executando step {current_step_index}/{len(workflow.get('steps', []))-1}")
                self.job_handler.update_job_status(job_id, step['status_update'])
                print(f"[{job_id}] [DEBUG] Antes de chamar _execute_step_with_strategy para step {current_step_index} (analysis_type={analysis_type})")
                step_result = self._execute_step_with_strategy(
                    job_id, job_info, step, current_step_index, previous_step_result, i, start_from_step
                )
                print(f"[{job_id}] [DEBUG] Depois de _execute_step_with_strategy para step {current_step_index} (analysis_type={analysis_type}), resultado: {str(step_result)[:300]}...")
                if current_step_index == 0:
                    print(f"[{job_id}] [DEBUG] Step 0: resultado do agente: {str(step_result)[:300]}...")
                    report_text = self.report_handler.extract_report_text(step_result)
                    if report_text and report_text.strip():
                        print(f"[{job_id}] [DEBUG] Step 0: relatório gerado, salvando...")
                        self._save_generated_report(job_id, job_info, step_result, current_step_index)
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
                self.job_handler.update_job_status(job_id, 'completed')
        except Exception as e:
            error_message = str(e)
            print(f"[{job_id}] ERRO FATAL NO WORKFLOW: {error_message}")
            traceback.print_exc()
            try:
                if job_info and 'data' in job_info:
                    job_info['data']['error_details'] = error_message
                    self.job_handler.update_job(job_id, job_info)
            except Exception as update_err:
                print(f"[{job_id}] ERRO CRÍTICO: Falha ao salvar detalhes do erro no job: {update_err}")
            self.job_handler.update_job_status(job_id, 'failed')
    def _execute_step_with_strategy(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], 
                                    current_step_index: int, previous_step_result: Dict[str, Any], 
                                    step_iteration: int, start_from_step: int) -> Dict[str, Any]:
        model_para_etapa = step.get('model_name', job_info.get('data', {}).get('model_name'))
        agent_type = step.get('agent_type', step.get('agent'))
        analysis_type = job_info['data'].get('original_analysis_type')
        agent_params = step.get('params', {}).copy() if step.get('params') else {}
        agent_params['instrucoes_extras'] = job_info['data'].get('instrucoes_extras', '')
        repo_name = job_info['data'].get('repo_name_modernizado')
        branch_name = job_info['data'].get('branch_name_modernizado')
        if branch_name:
            agent_params['nome_branch'] = branch_name
        agent_params['repositorio'] = repo_name
        agent_params.update({
            'usar_rag': job_info.get("data", {}).get("usar_rag", False), 
            'model_name': model_para_etapa,
            'repository_type': job_info['data']['repository_type'],
            'retornar_lista_arquivos': job_info.get('data', {}).get('retornar_lista_arquivos', False),
            'usuario_executor': job_info.get('data', {}).get('usuario_executor'),
            'job_id': job_id
        })
        strategy = StepStrategyFactory.create_strategy(step, self.job_handler)
        print(f"[{job_id}] [DEBUG] Chamando strategy.execute_step para agent_type={agent_type}, step={current_step_index}")
        result = strategy.execute_step(
            job_id, job_info, step, current_step_index, 
            previous_step_result, None, None, agent_params
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
