import re
from typing import List, Dict, Any, Optional
from tools.azure_secret_manager import AzureSecretManager
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
import requests
from services.task_parser_service import TaskParserService

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
                return {
                    'error': response.text,
                    'status_code': response.status_code
                }
        except Exception as e:
            return {
                'error': str(e)
            }

    def create_tasks_from_report(self, epic_id: str, markdown_table: str) -> List[Dict[str, Any]]:
        parser = TaskParserService()
        tasks = parser.parse_tasks_from_markdown(markdown_table)
        token = self._get_token()
        created_tasks = []
        total_tasks = len(tasks)
        success_count = 0
        error_count = 0
        for idx, task in enumerate(tasks):
            work_item_type = task.get('tipo', 'Task').capitalize()
            if work_item_type not in ['Task', 'Feature', 'Bug', 'Spike']:
                work_item_type = 'Task'
            title = task.get('titulo', '')
            descricao = task.get('descricao', '')
            criterios_aceite = task.get('criterios_aceite', '')
            perfis_sugeridos = task.get('perfis_sugeridos', '')
            estimativa_sp = task.get('estimativa_sp', '')
            description_full = descricao
            if criterios_aceite:
                description_full += '\n\nCritérios de Aceite:\n' + criterios_aceite
            if perfis_sugeridos:
                description_full += f"\n\nPerfis Sugeridos: {perfis_sugeridos}"
            url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/workitems/${work_item_type}?api-version=7.1-preview.3"
            headers = {
                'Content-Type': 'application/json-patch+json',
                'Authorization': f'Basic {self._basic_auth_header(token)}'
            }
            payload = [
                {"op": "add", "path": "/fields/System.Title", "from": None, "value": title},
                {"op": "add", "path": "/fields/System.Description", "from": None, "value": description_full},
                {"op": "add", "path": "/fields/System.Parent", "from": None, "value": int(epic_id)}
            ]
            if estimativa_sp:
                try:
                    sp_val = float(estimativa_sp)
                    payload.append({"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.StoryPoints", "from": None, "value": sp_val})
                except Exception:
                    pass
            print(f"[AzureBoardService] [DEBUG] ANTES de requests.post: url={url}")
            print(f"[AzureBoardService] [DEBUG] headers: {{'Content-Type': '{headers['Content-Type']}', 'Authorization': 'Basic <hidden>'}}")
            print(f"[AzureBoardService] [DEBUG] payload: {payload}")
            try:
                response = requests.post(url, headers=headers, json=payload)
                print(f"[AzureBoardService] [DEBUG] DEPOIS de requests.post: response.status_code={response.status_code}")
                print(f"[AzureBoardService] [DEBUG] response.text: {response.text}")
                if response.status_code in (200, 201):
                    data = response.json()
                    created_tasks.append({
                        "id": data.get("id"),
                        "url": data.get("url"),
                        "title": title
                    })
                    success_count += 1
                else:
                    created_tasks.append({
                        "error": response.text,
                        "title": title
                    })
                    error_count += 1
            except Exception as e:
                print(f"[AzureBoardService] [ERROR] Exception ao criar tarefa: {str(e)}")
                created_tasks.append({
                    "error": str(e),
                    "title": title
                })
                error_count += 1
                continue
        print(f"[AzureBoardService] [SUMMARY] Total de tarefas processadas: {total_tasks}, criadas com sucesso: {success_count}, com erro: {error_count}")
        return created_tasks
