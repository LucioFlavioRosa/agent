from services.workflow_finalizers.workflow_finalizer_interface import IWorkflowFinalizer

class EpicCreationWorkflowFinalizer(IWorkflowFinalizer):
    def __init__(self, azure_devops_service, job_handler):
        self.azure_devops_service = azure_devops_service
        self.job_handler = job_handler

    def finalize(self, job_id, job_info, workflow, final_result, repository_type, repo_name):
        epic_title = job_info['data'].get('epic_title') or 'Épico gerado pelo MCP'
        epic_description = job_info['data'].get('analysis_report') or ''
        organization = job_info['data'].get('azure_organization')
        project = job_info['data'].get('azure_project')
        board = job_info['data'].get('azure_board')
        epic_id = self.azure_devops_service.create_epic(
            organization=organization,
            project=project,
            board=board,
            title=epic_title,
            description=epic_description
        )
        job_info['data']['epic_id'] = epic_id
        self.job_handler.update_job(job_id, job_info)
        self.job_handler.update_job_status(job_id, 'completed')
