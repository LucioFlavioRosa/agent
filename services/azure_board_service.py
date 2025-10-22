import re
from typing import List, Dict, Any
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from tools.azure_secret_manager import AzureSecretManager

class AzureBoardService:
    def __init__(self, organization: str, project: str, secret_manager: AzureSecretManager):
        self.organization = organization
        self.project = project
        self.secret_manager = secret_manager
        self.connection = None
        self.core_client = None
        self.work_item_tracking_client = None
        self._connect()

    def _connect(self):
        token = self.secret_manager.get_secret(f"azure-token-{self.organization}")
        credentials = BasicAuthentication('', token)
        org_url = f"https://dev.azure.com/{self.organization}"
        self.connection = Connection(base_url=org_url, creds=credentials)
        self.core_client = self.connection.clients.get_core_client()
        self.work_item_tracking_client = self.connection.clients.get_work_item_tracking_client()

    def _parse_markdown_table(self, markdown_table: str) -> List[Dict[str, Any]]:
        lines = [line for line in markdown_table.split('\n') if line.strip()]
        if not lines or len(lines) < 3:
            return []
        header = lines[0].split('|')[1:-1]
        result = []
        for line in lines[2:]:
            columns = [col.strip() for col in line.split('|')[1:-1]]
            if len(columns) != len(header):
                continue
            epic = dict(zip([h.strip() for h in header], columns))
            result.append(epic)
        return result

    def create_epics(self, markdown_table: str) -> List[str]:
        epics = self._parse_markdown_table(markdown_table)
        created_epic_ids = []
        for epic in epics:
            fields = {
                'System.Title': epic.get('Épico', 'Épico sem nome'),
                'System.Description': f"Objetivo de Negócio: {epic.get('Objetivo de Negócio', '')}\n\nCritérios de Aceite / Atividades Chave:\n{epic.get('Critérios de Aceite / Atividades Chave', '')}\n\nPerfis Envolvidos: {epic.get('Perfis Envolvidos', '')}\nEstimativa: {epic.get('Estimativa de Esforço', '')}",
            }
            try:
                work_item = self.work_item_tracking_client.create_work_item(
                    document=[
                        {"op": "add", "path": "/fields/System.Title", "value": fields['System.Title']},
                        {"op": "add", "path": "/fields/System.Description", "value": fields['System.Description']}
                    ],
                    project=self.project,
                    type="Epic"
                )
                created_epic_ids.append(str(work_item.id))
            except Exception as e:
                created_epic_ids.append(f"ERRO: {str(e)}")
        return created_epic_ids
