from services.workflow_finalizers.workflow_finalizer_interface import IWorkflowFinalizer

class AzureDevOpsWorkflowFinalizer(IWorkflowFinalizer):
    def __init__(self, azure_devops_service, job_handler):
        self.azure_devops_service = azure_devops_service
        self.job_handler = job_handler

    def finalize(self, job_id, job_info, workflow, final_result, repository_type, repo_name):
        epic_title = job_info['data'].get('epic_title') or 'Épico gerado pelo MCP'
        epic_description = job_info['data'].get('epic_description') or ''
        tasks_json = final_result.get('tasks_json') if isinstance(final_result, dict) else None
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
        job_info['data']['epic_id'] = epic_id
        job_info['data']['task_ids'] = task_ids
        self.job_handler.update_job(job_id, job_info)
        self.job_handler.update_job_status(job_id, 'completed')
