from services.step_executors.base_step_executor import BaseStepExecutor
from services.azure_devops_service import AzureDevOpsService
from tools.epic_markdown_parser import EpicMarkdownParser
from tools.azure_secret_manager import AzureSecretManager
import base64

class EpicAzureDevOpsStepExecutor(BaseStepExecutor):
    def __init__(self, azure_devops_service=None, epic_parser=None, job_handler=None, secret_manager=None):
        self.azure_devops_service = azure_devops_service or AzureDevOpsService()
        self.epic_parser = epic_parser or EpicMarkdownParser()
        self.job_handler = job_handler
        self.secret_manager = secret_manager or AzureSecretManager()

    def _get_token(self, organization):
        token_secret_name = f"azure-token-{organization}"
        try:
            token = self.secret_manager.get_secret(token_secret_name)
            return token
        except Exception:
            try:
                token = self.secret_manager.get_secret("azure-token")
                return token
            except Exception:
                raise ValueError(f"Não foi possível obter token para Azure DevOps (org: {organization})")

    def execute(self, job_id, job_info, step, current_step_index, previous_step_result, repo_reader, agent_params):
        report_text = job_info['data'].get('analysis_report') or previous_step_result.get('analysis_report')
        if not report_text:
            raise ValueError(f"[{job_id}] Nenhum relatório de épicos disponível para parsing.")
        organization = agent_params.get('azure_organization') or job_info['data'].get('azure_organization')
        project = agent_params.get('azure_project') or job_info['data'].get('azure_project')
        board = agent_params.get('azure_board') or job_info['data'].get('azure_board')
        if not organization or not project or not board:
            raise ValueError(f"[{job_id}] Parâmetros obrigatórios ausentes para criação de épicos: organization, project, board.")
        token = self._get_token(organization)
        epics = []
        epic_ids = []
        parsed_epics = self.epic_parser.parse(report_text)
        for epic in parsed_epics:
            title = epic.get('epic_title') or epic.get('Épico')
            description = epic.get('objetivo_negocio') or epic.get('Objetivo de Negócio')
            epic_id = None
            epic_url = None
            try:
                result = self.azure_devops_service.create_epic(
                    organization=organization,
                    project=project,
                    board=board,
                    title=title,
                    description=description,
                    token=token
                )
                epic_id = result.get('epic_id')
                epic_url = result.get('epic_url')
            except Exception as e:
                print(f"[{job_id}] Falha ao criar épico '{title}': {e}")
                continue
            epic_dict = {
                "epic_id": epic_id,
                "epic_url": epic_url,
                "epic_title": title
            }
            epics.append(epic_dict)
            epic_ids.append(epic_id)
        job_info['data']['epic_ids'] = epic_ids
        job_info['data']['epics'] = epics
        self.job_handler.update_job(job_id, job_info)
        return {
            "epic_ids": epic_ids,
            "epics": epics,
            "step_index": current_step_index
        }
