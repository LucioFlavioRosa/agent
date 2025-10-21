from services.step_executors.base_step_executor import BaseStepExecutor

class EpicAzureDevOpsStepExecutor(BaseStepExecutor):
    def __init__(self, azure_devops_service, epic_parser, job_handler):
        self.azure_devops_service = azure_devops_service
        self.epic_parser = epic_parser
        self.job_handler = job_handler

    def execute(self, job_id, job_info, step, current_step_index, previous_step_result, repo_reader, agent_params):
        analysis_report = job_info['data'].get('analysis_report')
        if not analysis_report:
            raise ValueError(f"[{job_id}] Nenhum relatório de épicos aprovado encontrado para criação no Azure Boards.")
        epics = self.epic_parser.parse_epic_table(analysis_report)
        organization = job_info['data'].get('azure_organization')
        project = job_info['data'].get('azure_project')
        board = job_info['data'].get('azure_board')
        epic_ids = []
        for epic in epics:
            epic_id = self.azure_devops_service.create_epic(
                organization=organization,
                project=project,
                board=board,
                title=epic.get('epico'),
                description=epic.get('objetivo_negocio'),
                criterios_aceite=epic.get('criterios_aceite'),
                perfis_envolvidos=epic.get('perfis_envolvidos'),
                estimativa_esforco=epic.get('estimativa_esforco')
            )
            epic_ids.append(epic_id)
        self.job_handler.save_epic_ids(job_id, epic_ids)
        return {
            "job_id": job_id,
            "step_type": "epic_azure_writer",
            "epic_ids": epic_ids,
            "step_index": current_step_index
        }
