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

    def create_backlog_from_epic(self, epic_id: str) -> Dict[str, Any]:
        if not self.organization or not self.project:
            return {"error": "organization e project devem estar definidos para criar backlog."}
        try:
            epic_data = self.read_epic(epic_id)
            if 'error' in epic_data or not epic_data.get('title'):
                return {"error": f"Não foi possível ler o épico ou título ausente: {epic_data.get('error', 'Título ausente')}"}
            backlog_name = epic_data['title']
            token = self._get_token()
            url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/workitems/$Backlog?api-version=7.1-preview.3"
            headers = {
                'Content-Type': 'application/json-patch+json',
                'Authorization': f'Basic {self._basic_auth_header(token)}'
            }
            payload = [
                {"op": "add", "path": "/fields/System.Title", "from": None, "value": backlog_name},
                {"op": "add", "path": "/fields/System.Description", "from": None, "value": f"Backlog criado a partir do épico {epic_id}"}
            ]
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code in (200, 201):
                data = response.json()
                return {
                    "id": data.get("id"),
                    "url": data.get("url"),
                    "title": backlog_name
                }
            else:
                return {
                    "error": response.text,
                    "status_code": response.status_code
                }
        except Exception as e:
            return {"error": str(e)}

    def create_tasks_from_report(self, epic_id: str, markdown_table: str, backlog_id: Optional[str] = None) -> List[Dict[str, Any]]:
        parser = TaskParserService()
        tasks = parser.parse_tasks_from_markdown(markdown_table)
        print(f"[AzureBoardService] [DEBUG] Número de tarefas parseadas: {len(tasks)}")
        token = self._get_token()
        created_tasks = []
        total_tasks = len(tasks)
        success_count = 0
        error_count = 0
        parent_url = None
        parent_type = None
        if backlog_id:
            parent_url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/workitems/{backlog_id}"
            parent_type = 'Backlog'
        else:
            parent_url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/workitems/{epic_id}"
            parent_type = 'Epic'
        api_url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/workitems/$Task?api-version=7.1-preview.3"
        for idx, task in enumerate(tasks):
            print(f"[AzureBoardService] [DEBUG] Processando tarefa {idx+1}/{total_tasks}: {task}")
            if not task.get('titulo') or not task.get('descricao'):
                print(f"[AzureBoardService] [ERROR] Tarefa sem campos obrigatórios (titulo/descricao) - ignorando: {task}")
                created_tasks.append({
                    "error": "Campos obrigatórios ausentes (titulo/descricao)",
                    "task": task
                })
                error_count += 1
                continue
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
            payload = [
                {"op": "add", "path": "/fields/System.Title", "value": title},
                {"op": "add", "path": "/fields/System.Description", "value": f"<div>{description_full}</div>"}
            ]
            if estimativa_sp:
                try:
                    sp_val = float(estimativa_sp)
                    payload.append({"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.StoryPoints", "value": sp_val})
                except Exception:
                    print(f"[AzureBoardService] [WARN] Estimativa (SP) inválida para a tarefa '{title}': {estimativa_sp}")
            payload.append({
                "op": "add",
                "path": "/relations/-",
                "value": {
                    "rel": "System.LinkTypes.Hierarchy-Reverse",
                    "url": parent_url,
                    "attributes": {
                        "comment": f"Tarefa adicionada via script Python (parent: {parent_type})"
                    }
                }
            })
            headers = {
                'Content-Type': 'application/json-patch+json',
                'Authorization': f'Basic {self._basic_auth_header(token)}'
            }
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                try:
                    print(f"[AzureBoardService] [DEBUG] Tentativa {attempt} de criação da tarefa '{title}' no Azure DevOps...")
                    print(f"[AzureBoardService] [DEBUG] Payload: {json.dumps(payload, ensure_ascii=False)}")
                    response = requests.post(
                        f"https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/workitems/${work_item_type}?api-version=7.1-preview.3",
                        headers=headers,
                        data=json.dumps(payload)
                    )
                    print(f"[AzureBoardService] [DEBUG] Status code: {response.status_code}")
                    print(f"[AzureBoardService] [DEBUG] Response text: {response.text}")
                    if response.status_code in (200, 201):
                        try:
                            data = response.json()
                            created_tasks.append({
                                "id": data.get("id"),
                                "url": data.get("url"),
                                "title": title
                            })
                            success_count += 1
                        except Exception as e:
                            print(f"[AzureBoardService] [ERROR] Exception ao processar JSON de resposta: {str(e)}")
                            created_tasks.append({
                                "error": f"Erro ao processar JSON de resposta: {str(e)}",
                                "status_code": response.status_code,
                                "title": title
                            })
                            error_count += 1
                        break
                    else:
                        print(f"[AzureBoardService] [ERROR] Erro na criação da tarefa: status_code={response.status_code} - {response.text}")
                        if attempt == max_attempts:
                            created_tasks.append({
                                "error": response.text,
                                "status_code": response.status_code,
                                "title": title
                            })
                            error_count += 1
                        else:
                            wait_time = 2 ** attempt
                            print(f"[AzureBoardService] [WARN] Tentando novamente em {wait_time} segundos...")
                            time.sleep(wait_time)
                except requests.exceptions.RequestException as e:
                    print(f"[AzureBoardService] [ERROR] Exception ao criar tarefa: {str(e)}")
                    if hasattr(e, 'response') and e.response is not None:
                        print(f"   Status Code: {e.response.status_code}")
                        print(f"   Detalhes do erro: {e.response.text}")
                        if attempt == max_attempts:
                            created_tasks.append({
                                "error": e.response.text,
                                "status_code": e.response.status_code,
                                "title": title
                            })
                            error_count += 1
                        else:
                            wait_time = 2 ** attempt
                            print(f"[AzureBoardService] [WARN] Tentando novamente em {wait_time} segundos...")
                            time.sleep(wait_time)
                    else:
                        if attempt == max_attempts:
                            created_tasks.append({
                                "error": str(e),
                                "title": title
                            })
                            error_count += 1
                        else:
                            wait_time = 2 ** attempt
                            print(f"[AzureBoardService] [WARN] Tentando novamente em {wait_time} segundos...")
                            time.sleep(wait_time)
                    continue
        print(f"[AzureBoardService] [SUMMARY] Total de tarefas processadas: {total_tasks}, criadas com sucesso: {success_count}, com erro: {error_count}")
        return created_tasks

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

    def create_backlog_and_tasks_from_epic(self, epic_id: str, markdown_table: str) -> Dict[str, Any]:
        backlog_result = self.create_backlog_from_epic(epic_id)
        if 'error' in backlog_result or not backlog_result.get('id'):
            return {
                'error': backlog_result.get('error', 'Erro ao criar backlog'),
                'backlog': backlog_result,
                'tasks': []
            }
        backlog_id = backlog_result['id']
        tasks_result = self.create_tasks_from_report(epic_id, markdown_table, backlog_id=backlog_id)
        return {
            'backlog': backlog_result,
            'tasks': tasks_result
        }
