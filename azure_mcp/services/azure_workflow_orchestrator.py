import json
import traceback
from services.azure_board_service import AzureBoardService
from services.task_discussion_updater_service import TaskDiscussionUpdaterService
from services.epic_reader_service import EpicReaderService
from services.feature_reader_service import FeatureReaderService
from services.feature_parser_service import FeatureParserService
from services.task_parser_service import TaskParserService
from services.task_discussion_parser_service import TaskDiscussionParserService
from services.priority_mapper_service import PriorityMapperService
from models import JobFields

class AzureWorkflowOrchestrator:
    def __init__(self, job_manager, blob_storage, workflow_registry, secret_manager=None):
        self.workflow_registry = workflow_registry
        self.job_manager = job_manager
        self.blob_storage = blob_storage
        self.secret_manager = secret_manager

    def execute_workflow(self, job_id, start_from_step=0):
        job_info = self.job_manager.get_job_info(job_id)
        analysis_type = job_info['data'].get('original_analysis_type', '')
        organization = job_info['data'].get('organization') or job_info['data'].get('azure_organization')
        project = job_info['data'].get('project') or job_info['data'].get('azure_project')
        azure_board_service = AzureBoardService(organization, project, self.secret_manager)
        try:
            if analysis_type == 'criacao_tarefas_azure_devops':
                feature_id = job_info['data'].get('feature_id')
                if not feature_id:
                    raise ValueError(f"[{job_id}] ERRO: feature_id ausente para análise de tarefas Azure DevOps.")
                feature_data = azure_board_service.read_feature(feature_id)
                job_info['data']['feature_title'] = feature_data.get('title')
                job_info['data']['feature_description'] = feature_data.get('description')
                job_info['data']['feature_acceptance_criteria'] = feature_data.get('acceptance_criteria')
                job_info['data']['feature_data'] = feature_data
                report = job_info['data'].get('analysis_report')
                if start_from_step > 0:
                    if not report or not report.strip():
                        raise ValueError(f"[{job_id}] ERRO: Relatório de tarefas ausente ou vazio para criação de tarefas no Azure.")
                    created_tasks = azure_board_service.create_tasks_from_report_for_feature(feature_id, report)
                    if created_tasks and any('error' in task for task in created_tasks):
                        job_info['data']['tarefas_criadas_erro'] = created_tasks
                        self.job_manager.update_job(job_id, job_info)
                        self.job_manager.update_job_status(job_id, 'failed')
                        return
                    job_info['data']['tarefas_criadas'] = created_tasks
                    self.job_manager.update_job(job_id, job_info)
                    self.job_manager.update_job_status(job_id, 'completed')
                    return
            elif analysis_type == 'criacao_features_azure_devops':
                epic_id = job_info['data'].get('epic_id')
                report = job_info['data'].get('analysis_report')
                if start_from_step > 0:
                    if not epic_id:
                        raise ValueError(f"[{job_id}] ERRO: epic_id ausente para análise de features Azure DevOps.")
                    if not report or not report.strip():
                        raise ValueError(f"[{job_id}] ERRO: Relatório de features ausente ou vazio para criação de features no Azure.")
                    created_features = azure_board_service.create_features_from_epic(epic_id, report)
                    if created_features and any('error' in feature for feature in created_features):
                        job_info['data']['features_criadas_erro'] = created_features
                        self.job_manager.update_job(job_id, job_info)
                        self.job_manager.update_job_status(job_id, 'failed')
                        return
                    job_info['data']['features_criadas'] = created_features
                    self.job_manager.update_job(job_id, job_info)
                    self.job_manager.update_job_status(job_id, 'completed')
                    return
            elif analysis_type == 'criacao_epicos_azure_devops':
                report = job_info['data'].get('analysis_report')
                if start_from_step > 0:
                    created_epics = azure_board_service.create_epics(report)
                    job_info['data']['epicos_criados'] = created_epics
                    self.job_manager.update_job(job_id, job_info)
                    self.job_manager.update_job_status(job_id, 'completed')
                    return
            elif analysis_type == 'revisor_tarefas':
                task_id = job_info['data'].get('task_id')
                report = job_info['data'].get('analysis_report')
                if start_from_step > 0:
                    task_discussion_updater_service = TaskDiscussionUpdaterService()
                    update_result = task_discussion_updater_service.update_task_from_report(task_id, report, azure_board_service)
                    job_info['data']['task_discussion_update_result'] = update_result
                    self.job_manager.update_job(job_id, job_info)
                    if update_result.get('error') or (not update_result.get('success', True)):
                        self.job_manager.update_job_status(job_id, 'failed')
                        return
                    self.job_manager.update_job_status(job_id, 'completed')
                    return
            else:
                raise ValueError(f"[{job_id}] Analysis type '{analysis_type}' não suportado pelo AzureWorkflowOrchestrator.")
        except Exception as e:
            error_message = str(e)
            job_info['data']['error_details'] = error_message
            self.job_manager.update_job(job_id, job_info)
            self.job_manager.update_job_status(job_id, 'failed')
