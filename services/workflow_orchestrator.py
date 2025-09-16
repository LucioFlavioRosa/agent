from typing import Dict, Any
from domain.interfaces.workflow_orchestrator_interface import IWorkflowOrchestrator
from domain.interfaces.job_manager_interface import IJobManager
from domain.interfaces.changeset_filler_interface import IChangesetFiller
from domain.interfaces.report_manager_interface import IReportManager
from domain.interfaces.commit_manager_interface import ICommitManager
from domain.interfaces.approval_handler_interface import IApprovalHandler
from domain.interfaces.rag_retriever_interface import IRAGRetriever
from services.agent_executor import AgentExecutor
from tools.readers.reader_geral import ReaderGeral
from tools.repository_provider_factory import get_repository_provider_explicit

class WorkflowOrchestrator(IWorkflowOrchestrator):
    def __init__(self, 
                 job_manager: IJobManager, 
                 workflow_registry: Dict[str, Any],
                 changeset_filler: IChangesetFiller,
                 report_manager: IReportManager,
                 commit_manager: ICommitManager,
                 approval_handler: IApprovalHandler,
                 rag_retriever: IRAGRetriever):
        self.job_manager = job_manager
        self.workflow_registry = workflow_registry
        self.changeset_filler = changeset_filler
        self.report_manager = report_manager
        self.commit_manager = commit_manager
        self.approval_handler = approval_handler
        self.agent_executor = AgentExecutor(rag_retriever)

    def execute_workflow(self, job_id: str, start_from_step: int = 0) -> None:
        job_info = self.job_manager.get_job(job_id)
        if not job_info:
            raise ValueError("Job não encontrado.")

        workflow = self.workflow_registry.get(job_info['data']['original_analysis_type'])
        if not workflow:
            raise ValueError("Workflow não encontrado.")
            
        try:
            repository_type = job_info['data']['repository_type']
            repo_name = job_info['data']['repo_name']
            repository_provider = get_repository_provider_explicit(repository_type)
            repo_reader = ReaderGeral(repository_provider=repository_provider)

            previous_step_result = job_info['data'].get(f'step_{start_from_step - 1}_result', {})
            steps_to_run = workflow.get('steps', [])[start_from_step:]

            for i, step in enumerate(steps_to_run):
                current_step_index = start_from_step + i
                self.job_manager.update_job_status(job_id, step['status_update'])

                if current_step_index == 0:
                    existing_report_result = self.report_manager.try_read_existing_report(job_id, job_info, current_step_index)
                    if existing_report_result:
                        print(f"[{job_id}] Relatório existente encontrado no Blob Storage")

                        report_data = self._extract_report_data(existing_report_result)
                        report_text = report_data.get('relatorio', '')

                        job_info['data']['analysis_report'] = report_text
                        job_info['data'][f'step_{current_step_index}_result'] = report_data

                        if self._should_generate_report_only(job_info, current_step_index):
                            print(f"[{job_id}] Modo 'gerar_relatorio_apenas' ativo com relatório existente. Finalizando.")
                            self.job_manager.update_job_status(job_id, 'completed')
                            return

                        if step.get('requires_approval'):
                            print(f"[{job_id}] Relatório existente carregado. Pausando para aprovação do usuário.")
                            self.approval_handler.handle_approval_step(job_id, job_info, current_step_index, report_data)
                            return

                        previous_step_result = report_data
                        continue
                    else:
                        print(f"[{job_id}] Relatório não encontrado no Blob Storage, gerando novo relatório via agente")

                step_result = self.agent_executor.execute_step(
                    job_id, job_info, step, current_step_index, previous_step_result, repo_reader
                )

                job_info['data'][f'step_{current_step_index}_result'] = step_result
                previous_step_result = step_result

                if self._should_generate_report_only(job_info, current_step_index):
                    self.report_manager.handle_report_only_mode(job_id, job_info, step_result)
                    return

                if step.get('requires_approval'):
                    self.approval_handler.handle_approval_step(job_id, job_info, current_step_index, step_result)
                    return

            self._finalize_workflow(job_id, job_info, workflow, previous_step_result, repository_type, repo_name)

        except Exception as e:
            self.job_manager.handle_job_error(job_id, e, 'workflow')

    def handle_approval_step(self, job_id: str, step_index: int, step_result: Dict[str, Any]) -> None:
        job_info = self.job_manager.get_job(job_id)
        self.approval_handler.handle_approval_step(job_id, job_info, step_index, step_result)

    def _extract_report_data(self, existing_report_result: Dict[str, Any]) -> Dict[str, Any]:
        import json
        json_string = existing_report_result['resultado']['reposta_final']['reposta_final']
        return json.loads(json_string)

    def _should_generate_report_only(self, job_info: Dict[str, Any], current_step_index: int) -> bool:
        return current_step_index == 0 and job_info['data'].get('gerar_relatorio_apenas') is True

    def _finalize_workflow(self, job_id: str, job_info: Dict[str, Any], workflow: Dict[str, Any], 
                          final_result: Dict[str, Any], repository_type: str, repo_name: str) -> None:

        workflow_steps = workflow.get("steps", [])
        num_total_steps = len(workflow_steps)

        resultado_agrupamento = final_result
        resultado_refatoracao = {}

        if num_total_steps >= 2:
            penultimate_step_index = num_total_steps - 2
            resultado_refatoracao = job_info['data'].get(f'step_{penultimate_step_index}_result', {})
        elif num_total_steps == 1:
            resultado_refatoracao = final_result

        job_info['data']['diagnostic_logs'] = {
            "penultimate_result": resultado_refatoracao,
            "final_result": resultado_agrupamento
        }

        self.job_manager.update_job_status(job_id, 'populating_data')

        dados_preenchidos = self.changeset_filler.main(
            json_agrupado=resultado_agrupamento,
            json_inicial=resultado_refatoracao
        )

        dados_finais_formatados = self.commit_manager.format_final_data(dados_preenchidos)

        self.job_manager.update_job_status(job_id, 'committing_to_github')

        self.commit_manager.execute_commits(job_id, job_info, dados_finais_formatados, repository_type, repo_name)

        self.job_manager.update_job_status(job_id, 'completed')
        print(f"[{job_id}] Processo concluído com sucesso!")