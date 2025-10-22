import re
from typing import List, Dict, Any
from tools.azure_secret_manager import AzureSecretManager
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from azure.devops.v7_1.work_item_tracking.models import Wiql
from azure.devops.v7_1.work_item_tracking.work_item_tracking_client import WorkItemTrackingClient

class AzureBoardService:
    def __init__(self, organization: str, project: str, secret_manager: AzureSecretManager = None):
        self.organization = organization
        self.project = project
        self.secret_manager = secret_manager or AzureSecretManager()
        self.connection = None
        self.client = None
        self._connect()

    def _connect(self):
        token = self.secret_manager.get_secret(f"azure-token-{self.organization}")
        credentials = BasicAuthentication('', token)
        org_url = f"https://dev.azure.com/{self.organization}"
        self.connection = Connection(base_url=org_url, creds=credentials)
        self.client: WorkItemTrackingClient = self.connection.clients.get_work_item_tracking_client()

    def _parse_epics_from_markdown(self, markdown_table: str) -> List[Dict[str, Any]]:
        lines = [line for line in markdown_table.strip().split('\n') if line.strip()]
        if len(lines) < 3:
            return []
        header = lines[0].split('|')
        header = [h.strip() for h in header if h.strip()]
        epics = []
        for line in lines[2:]:
            cols = [c.strip() for c in line.split('|')][1:-1]
            if len(cols) != 6:
                continue
            epic = {
                'id': cols[0],
                'title': cols[1],
                'business_objective': cols[2],
                'acceptance_criteria': cols[3],
                'profiles': cols[4],
                'effort': cols[5]
            }
            epics.append(epic)
        return epics

    def create_epics(self, markdown_table: str) -> List[str]:
        epics = self._parse_epics_from_markdown(markdown_table)
        created_epic_ids = []
        for epic in epics:
            fields = {
                'System.Title': epic['title'],
                'System.Description': f"Objetivo de Negócio: {epic['business_objective']}\n\nCritérios de Aceite / Atividades Chave: {epic['acceptance_criteria']}\n\nPerfis Envolvidos: {epic['profiles']}\n\nEstimativa de Esforço: {epic['effort']}"
            }
            try:
                wi = self.client.create_work_item(
                    document=[
                        {"op": "add", "path": "/fields/System.Title", "value": fields['System.Title']},
                        {"op": "add", "path": "/fields/System.Description", "value": fields['System.Description']}
                    ],
                    project=self.project,
                    type="Epic"
                )
                created_epic_ids.append(str(wi.id))
            except Exception as e:
                created_epic_ids.append(f"ERROR: {str(e)}")
        return created_epic_ids
