from services.step_executors.base_step_executor import BaseStepExecutor
from services.azure_devops_service import AzureDevOpsService

class AzureDevOpsStepExecutor(BaseStepExecutor):
    def __init__(self, azure_devops_service=None):
        self.azure_devops_service = azure_devops_service or AzureDevOpsService()

    def execute(self, job_id, job_info, step, current_step_index, previous_step_result, repo_reader, agent_params):
        epic_title = agent_params.get('epic_title') or "Épico gerado pelo MCP"
        epic_description = agent_params.get('epic_description') or ""
        tasks_json = previous_step_result.get('tasks_json')
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
        task_ids = []
        if tasks_json and isinstance(tasks_json, dict) and 'lista_de_tarefas' in tasks_json:
            for task in tasks_json['lista_de_tarefas']:
                task_id = self.azure_devops_service.create_task(
                    organization=organization,
                    project=project,
                    board=board,
                    epic_id=epic_id,
                    titulo=task['titulo'],
                    descricao=task['descricao'],
                    criterios_de_aceite=task['criterios_de_aceite'],
                    perfis_sugeridos=task['perfis_sugeridos'],
                    estimativa_sp=task['estimativa_sp']
                )
                task_ids.append(task_id)
        return {
            "job_id": job_id,
            "step_type": "create_epic_and_tasks",
            "epic_id": epic_id,
            "task_ids": task_ids,
            "step_index": current_step_index
        }
