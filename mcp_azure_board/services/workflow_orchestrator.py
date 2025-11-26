import json
import traceback
from typing import Dict, Any, Optional
from models import JobFields
from services.azure_board_service import AzureBoardService
from services.report_handler import ReportHandler
from services.job_handler import JobHandler
from services.task_discussion_updater_service import TaskDiscussionUpdaterService

class WorkflowOrchestrator:
    def __init__(self, job_manager, blob_storage, workflow_registry, secret_manager=None):
        self.workflow_registry = workflow_registry
        self.job_handler = JobHandler(job_manager)
        self.report_handler = ReportHandler(blob_storage)
        self.secret_manager = secret_manager

    def _save_generated_report(self, job_id: str, job_info: Dict[str, Any], step_result: Dict[str, Any], current_step_index: int) -> bool:
        report_text = self.report_handler.extract_report_text(step_result)
        if not report_text or len(report_text.strip()) == 0:
            print(f"[{job_id}] ERRO: Relatório gerado pelo agente está vazio no step {current_step_index}.")
            return False
        job_info['data']['analysis_report'] = report_text
        url = self.report_handler.save_report_to_blob(job_id, job_info, report_text)
        if not url:
            raise ValueError(f"[{job_id}] ERRO CRÍTICO: Relatório não foi salvo no Blob Storage")
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
        analysis_type = job_info['data'].get('original_analysis_type', '')
        workflow = self.workflow_registry.get(analysis_type)
        if not workflow:
            raise ValueError("Workflow não encontrado.")
        try:
            organization = job_info['data'].get('organization') or job_info['data'].get('azure_organization')
            project = job_info['data'].get('project') or job_info['data'].get('azure_project')
            azure_board_service = AzureBoardService(organization, project, self.secret_manager)
            steps_to_run = workflow.get('steps', [])[start_from_step:]
            for i, step in enumerate(steps_to_run):
                current_step_index = start_from_step + i
                self.job_handler.update_job_status(job_id, step.get('status_update', 'processing'))
                step_result = None
                agent_type = step.get('agent_type', step.get('agent'))
                agent_params = step.get('params', {}).copy() if step.get('params') else {}
                agent_params['instrucoes_extras'] = job_info['data'].get('instrucoes_extras', '')
                agent_params['organization'] = organization
                agent_params['project'] = project
                agent_params['epic_id'] = job_info['data'].get('epic_id')
                agent_params['feature_id'] = job_info['data'].get('feature_id')
                agent_params['task_id'] = job_info['data'].get('task_id')
                agent_params['job_id'] = job_id
                # Executa agente revisor_board
                if agent_type == 'revisor_board':
                    from agents.agente_revisor_board import AgenteRevisorBoard
                    from services.factories.llm_provider_factory import LLMProviderFactory
                    model_para_etapa = step.get('model_name', job_info.get('data', {}).get('model_name'))
                    llm_provider = LLMProviderFactory.create_provider(model_para_etapa)
                    agent = AgenteRevisorBoard(azure_board_service=azure_board_service, llm_provider=llm_provider)
                    step_result = agent.main(
                        analysis_type=analysis_type,
                        instrucoes_extras=agent_params['instrucoes_extras'],
                        job_id=job_id,
                        projeto=project,
                        epic_id=agent_params['epic_id'],
                        feature_id=agent_params['feature_id'],
                        task_id=agent_params['task_id'],
                        model_name=model_para_etapa
                    )
                # Executa atualização de discussion de tarefas
                elif agent_type == 'task_discussion_updater':
                    report = job_info['data'].get('analysis_report')
                    task_id = agent_params['task_id']
                    updater = TaskDiscussionUpdaterService()
                    step_result = updater.update_task_from_report(task_id, report, azure_board_service)
                # Executa criação de épicos
                elif agent_type == 'epic_creator':
                    markdown_table = job_info['data'].get('analysis_report')
                    step_result = azure_board_service.create_epics(markdown_table)
                # Executa criação de features
                elif agent_type == 'feature_creator':
                    epic_id = agent_params['epic_id']
                    markdown_table = job_info['data'].get('analysis_report')
                    step_result = azure_board_service.create_features_from_epic(epic_id, markdown_table)
                # Executa criação de tarefas
                elif agent_type == 'task_creator':
                    feature_id = agent_params['feature_id']
                    markdown_table = job_info['data'].get('analysis_report')
                    step_result = azure_board_service.create_tasks_from_report_for_feature(feature_id, markdown_table)
                # Salvamento de relatório
                if current_step_index == 0:
                    self._save_generated_report(job_id, job_info, step_result, current_step_index)
                    if step.get('requires_approval', False):
                        self.handle_approval_step(job_id, job_info, current_step_index, step_result)
                        return
                job_info = self.job_handler.get_job_info(job_id)
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

    def handle_approval_step(self, job_id: str, job_info: Dict[str, Any], step_index: int, step_result: Dict[str, Any]) -> None:
        report_text = self.report_handler.extract_report_text(step_result)
        job_info['data']['analysis_report'] = report_text
        job_info['status'] = 'pending_approval'
        self.job_handler.set_paused_step(job_info, step_index)
        self.job_handler.update_job(job_id, job_info)
