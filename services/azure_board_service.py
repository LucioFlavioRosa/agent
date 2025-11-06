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

    def create_backlog_from_epic(self, epic_id: str) -> Dict[str, Any]:
        if not self.organization or not self.project:
            print(f"[AzureBoardService-DEBUG] organization e project não definidos para criar backlog.")
            return {"error": "organization e project devem estar definidos para criar backlog."}
        try:
            print(f"[AzureBoardService-DEBUG] Chamando EpicReaderService.get_epic_title com epic_id={epic_id}, organization={self.organization}, project={self.project}")
            epic_title = EpicReaderService.get_epic_title(epic_id, self.organization, self.project)
            print(f"[AzureBoardService-DEBUG] Título do épico obtido: epic_title={epic_title}")
            if not epic_title:
                print(f"[AzureBoardService-DEBUG] Não foi possível obter o título do épico {epic_id}.")
                return {"error": f"Não foi possível obter o título do épico {epic_id}. Verifique se o épico existe e se as credenciais estão corretas."}
            token = self._get_token()
            url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/workitems/$Product%20Backlog%20Item?api-version=7.1-preview.3"
            parent_epic_url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/workitems/{epic_id}"
            payload = [
                {"op": "add", "path": "/fields/System.Title", "from": None, "value": epic_title},
                {"op": "add", "path": "/fields/System.Description", "from": None, "value": f"Backlog criado a partir do épico {epic_id}"},
                {
                    "op": "add",
                    "path": "/relations/-",
                    "value": {
                        "rel": "System.LinkTypes.Hierarchy-Reverse",
                        "url": parent_epic_url
                    }
                }
            ]
            print(f"[AzureBoardService-DEBUG] Criando backlog. URL={url}, Payload={payload}")
            headers = {
                'Content-Type': 'application/json-patch+json',
                'Authorization': f'Basic {self._basic_auth_header(token)}'
            }
            response = requests.post(url, headers=headers, json=payload)
            print(f"[AzureBoardService-DEBUG] Resposta da criação do backlog. Status={response.status_code}, Body={response.text[:500]}")
            if response.status_code in (200, 201):
                data = response.json()
                print(f"[AzureBoardService-DEBUG] Backlog criado com sucesso. id={data.get('id')}, url={data.get('url')}, title={epic_title}")
                return {
                    "id": data.get("id"),
                    "url": data.get("url"),
                    "title": epic_title
                }
            else:
                print(f"[AzureBoardService-DEBUG] Falha ao criar backlog: {response.text}")
                return {
                    "error": response.text,
                    "status_code": response.status_code
                }
        except Exception as e:
            print(f"[AzureBoardService-DEBUG] Exceção ao criar backlog: {str(e)}")
            return {"error": str(e)}

    def create_tasks_from_report(self, epic_id: str, markdown_table: str) -> List[Dict[str, Any]]:
        if not epic_id or not markdown_table or not isinstance(markdown_table, str) or len(markdown_table.strip()) == 0:
            print(f"[AzureBoardService-DEBUG] ERRO: epic_id ou markdown_table inválidos. epic_id={epic_id}, len(markdown_table)={len(markdown_table) if markdown_table else 0}")
            raise ValueError(f"[AzureBoardService] ERRO: epic_id ou markdown_table inválidos. epic_id={epic_id}, len(markdown_table)={len(markdown_table) if markdown_table else 0}")
        print(f"[AzureBoardService-DEBUG] Chamando AzureBoardService.create_backlog_from_epic com epic_id={epic_id}")
        print(f"[AzureBoardService-DEBUG] ANTES de chamar create_backlog_from_epic. epic_id={epic_id}, self.organization={self.organization}, self.project={self.project}")
        backlog_result = self.create_backlog_from_epic(epic_id)
        print(f"[AzureBoardService-DEBUG] DEPOIS de chamar create_backlog_from_epic. backlog_result={backlog_result}")
        if 'error' in backlog_result or not backlog_result.get('id'):
            print(f"[AzureBoardService-DEBUG] Falha ao criar backlog: {backlog_result.get('error', 'Erro desconhecido')}")
            return [{"error": f"Falha ao criar backlog: {backlog_result.get('error', 'Erro desconhecido')}"}]
        backlog_id = backlog_result['id']
        backlog_url = backlog_result['url']
        parser = TaskParserService()
        print(f"[TaskParserService-DEBUG] Iniciando parsing. Tamanho do markdown: {len(markdown_table)} caracteres")
        tasks = parser.parse_tasks_from_markdown(markdown_table)
        print(f"[TaskParserService-DEBUG] Parsing concluído. Total de tarefas parseadas: {len(tasks)}")
        if len(tasks) == 0:
            print(f"[TaskParserService-WARNING] Nenhuma tarefa foi parseada da tabela Markdown. Verifique o formato da tabela.")
            return [{"error": "Nenhuma tarefa foi encontrada no relatório para criar no backlog."}]
        token = self._get_token()
        created_tasks = []
        total_tasks = len(tasks)
        parent_backlog_url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/workitems/{backlog_id}"
        for idx, task in enumerate(tasks):
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
                    pass
            payload.append({
                "op": "add",
                "path": "/relations/-",
                "value": {
                    "rel": "System.LinkTypes.Hierarchy-Reverse",
                    "url": parent_backlog_url,
                    "attributes": {
                        "comment": "Tarefa adicionada via script Python"
                    }
                }
            })
            headers = {
                'Content-Type': 'application/json-patch+json',
                'Authorization': f'Basic {self._basic_auth_header(token)}'
            }
            print(f"[AzureBoardService-DEBUG] Criando tarefa {idx+1}/{total_tasks}. Título: {title}, Payload: {json.dumps(payload)[:200]}")
            try:
                response = requests.post(
                    f"https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/workitems/$Task?api-version=7.1-preview.3",
                    headers=headers,
                    data=json.dumps(payload)
                )
                print(f"[AzureBoardService-DEBUG] Resposta da criação da tarefa {idx+1}. Status={response.status_code}, Body={response.text[:300]}")
                if response.status_code in (200, 201):
                    try:
                        data = response.json()
                        created_tasks.append({
                            "id": data.get("id"),
                            "url": data.get("url"),
                            "title": title
                        })
                    except Exception as e:
                        created_tasks.append({
                            "error": f"Erro ao processar JSON de resposta: {str(e)}",
                            "status_code": response.status_code,
                            "title": title
                        })
                else:
                    created_tasks.append({
                        "error": response.text,
                        "status_code": response.status_code,
                        "title": title
                    })
            except Exception as e:
                created_tasks.append({
                    "error": str(e),
                    "title": title
                })
        return created_tasks

    def update_task_discussion(self, task_id: str, discussion_entries: List[Dict[str, str]]) -> Dict[str, Any]:
        if not self.organization or not self.project:
            return {"error": "organization e project devem estar definidos para atualizar discussion da task."}
        token = self._get_token()
        url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/workitems/{task_id}/comments?api-version=7.1-preview.3"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {self._basic_auth_header(token)}'
        }
        created_comment_ids = []
        errors = []
        for entry in discussion_entries:
            categoria = entry.get('Categoria') or entry.get('categoria') or ''
            pergunta = entry.get('Pergunta') or entry.get('pergunta') or ''
            comment_body = f"**Categoria:** {categoria}\n**Pergunta:** {pergunta}"
            payload = {"text": comment_body}
            try:
                response = requests.post(url, headers=headers, json=payload)
                if response.status_code in (200, 201):
                    data = response.json()
                    comment_id = data.get('id')
                    created_comment_ids.append(comment_id)
                else:
                    errors.append({"error": response.text, "status_code": response.status_code, "payload": payload})
            except Exception as e:
                errors.append({"error": str(e), "payload": payload})
        result = {"success": len(errors) == 0, "comment_ids": created_comment_ids}
        if errors:
            result["errors"] = errors
        return result
