import re
from typing import List, Dict, Any, Optional
from tools.azure_secret_manager import AzureSecretManager
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
import requests
from services.task_parser_service import TaskParserService
import json
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from services.epic_reader_service import EpicReaderService

class AzureBoardService:
    def __init__(self, organization: Optional[str] = None, project: Optional[str] = None, secret_manager: AzureSecretManager = None):
        self.organization = organization
        self.project = project
        self.secret_manager = secret_manager or AzureSecretManager()
        self.connection = None
        self.core_client = None
        if self.organization and self.project:
            self._connect()

    def _connect(self):
        token = self._get_token()
        org_url = f'https://dev.azure.com/{self.organization}'
        credentials = BasicAuthentication('', token)
        self.connection = Connection(base_url=org_url, creds=credentials)
        self.core_client = self.connection.clients.get_core_client()

    def _get_token(self):
        token_secret_name = f"azure-token-{self.organization}" if self.organization else "azure-token"
        try:
            return self.secret_manager.get_secret(token_secret_name)
        except Exception:
            return self.secret_manager.get_secret("azure-token")

    def parse_epics_from_markdown(self, markdown_table: str) -> List[Dict[str, Any]]:
        lines = [line for line in markdown_table.splitlines() if line.strip() and not line.strip().startswith('|---')]
        header = None
        epics = []
        for line in lines:
            if line.startswith('|') and line.endswith('|'):
                cols = [col.strip() for col in line.strip('|').split('|')]
                if not header:
                    header = cols
                    continue
                if len(cols) != len(header):
                    continue
                epic = dict(zip(header, cols))
                epics.append(epic)
        return epics

    def create_epics(self, markdown_table: str) -> List[Dict[str, Any]]:
        epics = self.parse_epics_from_markdown(markdown_table)
        token = self._get_token()
        created_epics = []
        for epic in epics:
            title = epic.get('Épico') or epic.get('Epico') or epic.get('Epic')
            description = f"Objetivo: {epic.get('Objetivo de Negócio', '')}\n\nCritérios/Atividades:\n{epic.get('Critérios de Aceite / Atividades Chave', '')}\n\nPerfis: {epic.get('Perfis Envolvidos', '')}\nEstimativa: {epic.get('Estimativa de Esforço', '')}"
            url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/workitems/$Epic?api-version=7.1-preview.3"
            headers = {
                'Content-Type': 'application/json-patch+json',
                'Authorization': f'Basic {self._basic_auth_header(token)}'
            }
            payload = [
                {"op": "add", "path": "/fields/System.Title", "from": None, "value": title},
                {"op": "add", "path": "/fields/System.Description", "from": None, "value": description}
            ]
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code in (200, 201):
                data = response.json()
                created_epics.append({
                    "id": data.get("id"),
                    "url": data.get("url"),
                    "title": title
                })
            else:
                created_epics.append({
                    "error": response.text,
                    "title": title
                })
        return created_epics

    def _basic_auth_header(self, token):
        import base64
        return base64.b64encode(f':{token}'.encode('utf-8')).decode('utf-8')

    def read_epic(self, epic_id: str) -> Dict[str, Any]:
        if not self.organization or not self.project:
            raise ValueError("organization e project devem estar definidos para buscar épico.")
        token = self._get_token()
        url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/workitems/{epic_id}?api-version=7.1-preview.3"
        headers = {
            'Authorization': f'Basic {self._basic_auth_header(token)}'
        }
        try:
            response = requests.get(url, headers=headers)
            print(f"[AzureBoardService-DEBUG] read_epic: GET {url} status={response.status_code}")
            if response.status_code == 200:
                data = response.json()
                fields = data.get('fields', {})
                return {
                    'id': data.get('id'),
                    'title': fields.get('System.Title'),
                    'description': fields.get('System.Description'),
                    'state': fields.get('System.State'),
                    'url': data.get('url'),
                    'fields': fields
                }
            else:
                print(f"[AzureBoardService-DEBUG] read_epic: Falha ao buscar épico. status={response.status_code}, body={response.text}")
                return {
                    'error': response.text,
                    'status_code': response.status_code
                }
        except Exception as e:
            print(f"[AzureBoardService-DEBUG] read_epic: Exceção ao buscar épico: {str(e)}")
            return {
                'error': str(e)
            }

    def read_task(self, task_id: str) -> Dict[str, Any]:
        if not self.organization or not self.project:
            raise ValueError("organization e project devem estar definidos para buscar tarefa.")
        token = self._get_token()
        url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/workitems/{task_id}?api-version=7.1-preview.3"
        headers = {
            'Authorization': f'Basic {self._basic_auth_header(token)}'
        }
        try:
            print(f"[AzureBoardService-DEBUG] read_task: GET {url}")
            response = requests.get(url, headers=headers)
            print(f"[AzureBoardService-DEBUG] read_task: status={response.status_code}")
            if response.status_code == 200:
                data = response.json()
                fields = data.get('fields', {})
                print(f"[AzureBoardService-DEBUG] read_task: Dados retornados para task_id={task_id}: {json.dumps(fields)[:200]}...")
                return {
                    'id': data.get('id'),
                    'title': fields.get('System.Title'),
                    'description': fields.get('System.Description'),
                    'state': fields.get('System.State'),
                    'url': data.get('url'),
                    'fields': fields
                }
            else:
                print(f"[AzureBoardService-DEBUG] read_task: Falha ao buscar tarefa. status={response.status_code}, body={response.text}")
                return {
                    'error': response.text,
                    'status_code': response.status_code
                }
        except Exception as e:
            print(f"[AzureBoardService-DEBUG] read_task: Exceção ao buscar tarefa: {str(e)}")
            return {
                'error': str(e)
            }
