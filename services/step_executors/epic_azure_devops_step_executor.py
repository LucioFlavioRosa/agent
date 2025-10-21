from services.step_executors.base_step_executor import BaseStepExecutor
from services.azure_devops_service import AzureDevOpsService
from tools.epic_markdown_parser import EpicMarkdownParser
from tools.azure_secret_manager import AzureSecretManager

class EpicAzureDevOpsStepExecutor(BaseStepExecutor):
    def __init__(self, azure_devops_service=None, epic_parser=None, job_handler=None, secret_manager=None):
        self.azure_devops_service = azure_devops_service or AzureDevOpsService()
        self.epic_parser = epic_parser or EpicMarkdownParser()
        self.job_handler = job_handler
        self.secret_manager = secret_manager or AzureSecretManager()

    def _get_token(self, org_name):
        token_secret_name = f"azure-token-{org_name}"
        try:
            token = self.secret_manager.get_secret(token_secret_name)
            print(f"[EpicAzureDevOpsStepExecutor] Token específico encontrado: {token_secret_name}")
            return token
        except Exception:
            print(f"[EpicAzureDevOpsStepExecutor] Token específico '{token_secret_name}' não encontrado. Tentando fallback 'azure-token'.")
            try:
                token = self.secret_manager.get_secret("azure-token")
                print(f"[EpicAzureDevOpsStepExecutor] Token padrão 'azure-token' encontrado.")
                return token
            except Exception as e:
                print(f"[EpicAzureDevOpsStepExecutor] ERRO CRÍTICO: Nenhum token Azure encontrado.")
                raise ValueError(f"Nenhum token Azure encontrado. Verifique se existe '{token_secret_name}' ou 'azure-token' no gerenciador de segredos.") from e

    def execute(self, job_id, job_info, step, current_step_index, previous_step_result, repo_reader, agent_params):
        report_text = job_info['data'].get('analysis_report')
        if not report_text:
            raise ValueError(f"[{job_id}] Nenhum relatório de épicos encontrado para processamento.")
        epics = self.epic_parser.parse(report_text)
        if not epics or not isinstance(epics, list):
            raise ValueError(f"[{job_id}] Nenhum épico válido encontrado no relatório.")
        organization = agent_params.get('azure_organization') or job_info['data'].get('azure_organization')
        project = agent_params.get('azure_project') or job_info['data'].get('azure_project')
        board = agent_params.get('azure_board') or job_info['data'].get('azure_board')
        if not organization or not project or not board:
            raise ValueError(f"[{job_id}] Dados obrigatórios ausentes para criação de épicos: organization, project, board.")
        token = self._get_token(organization)
        epic_ids = []
        epics_data = []
        for epic in epics:
            title = epic.get('epic_title') or epic.get('Épico') or epic.get('epic')
            description = epic.get('objetivo_negocio') or epic.get('Objetivo de Negócio') or epic.get('objetivo')
            if not title or not description:
                print(f"[{job_id}] Épico ignorado por falta de título ou descrição.")
                continue
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
            epic_data = {
                'epic_id': epic_id,
                'epic_url': epic_url,
                'epic_title': title
            }
            epic_ids.append(epic_id)
            epics_data.append(epic_data)
        job_info['data']['epic_ids'] = epic_ids
        job_info['data']['epics'] = epics_data
        if self.job_handler:
            self.job_handler.update_job(job_id, job_info)
        return {
            "epic_ids": epic_ids,
            "epics": epics_data,
            "step_index": current_step_index
        }
