from domain.interfaces.azure_devops_service_interface import IAzureDevOpsService
import logging

class AzureDevOpsService(IAzureDevOpsService):
    def __init__(self, api_client=None):
        self.api_client = api_client

    def create_epic(self, organization, project, board, title, description):
        try:
            # Aqui seria feita a chamada real à API do Azure DevOps
            logging.info(f"[AzureDevOpsService] Criando épico: org={organization}, project={project}, board={board}, title={title}")
            epic_id = f"epic-{organization}-{project}-{board}-{title[:10]}"
            return epic_id
        except Exception as e:
            logging.error(f"[AzureDevOpsService] Erro ao criar épico: {e}")
            raise

    def create_task(self, organization, project, board, epic_id, titulo, descricao, criterios_de_aceite, perfis_sugeridos, estimativa_sp):
        try:
            # Aqui seria feita a chamada real à API do Azure DevOps
            logging.info(f"[AzureDevOpsService] Criando task: org={organization}, project={project}, board={board}, epic_id={epic_id}, titulo={titulo}")
            task_id = f"task-{epic_id}-{titulo[:10]}"
            return task_id
        except Exception as e:
            logging.error(f"[AzureDevOpsService] Erro ao criar task: {e}")
            raise
