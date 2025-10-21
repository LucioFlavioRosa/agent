from services.step_executors.base_step_executor import BaseStepExecutor
from services.azure_devops_service import AzureDevOpsService

class EpicCreationStepExecutor(BaseStepExecutor):
    def __init__(self, azure_devops_service=None):
        self.azure_devops_service = azure_devops_service or AzureDevOpsService()

    def execute(self, job_id, job_info, step, current_step_index, previous_step_result, repo_reader, agent_params):
        epic_title = agent_params.get('epic_title') or job_info['data'].get('epic_title') or 'Épico gerado pelo MCP'
        epic_description = agent_params.get('epic_description') or job_info['data'].get('analysis_report') or ''
        organization = agent_params.get('azure_organization') or job_info['data'].get('azure_organization')
        project = agent_params.get('azure_project') or job_info['data'].get('azure_project')
        board = agent_params.get('azure_board') or job_info['data'].get('azure_board')
        epic_id = self.azure_devops_service.create_epic(
            organization=organization,
            project=project,
            board=board,
            title=epic_title,
            description=epic_description
        )
        return {
            "job_id": job_id,
            "step_type": "create_epic",
            "epic_id": epic_id,
            "step_index": current_step_index
        }
