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
from services.feature_parser_service import FeatureParserService

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

    def read_feature(self, feature_id: str) -> Dict[str, Any]:
        if not self.organization or not self.project:
            raise ValueError("organization e project devem estar definidos para buscar feature.")
        token = self._get_token()
        url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/workitems/{feature_id}?api-version=7.1-preview.3"
        headers = {
            'Authorization': f'Basic {self._basic_auth_header(token)}'
        }
        try:
            response = requests.get(url, headers=headers)
            print(f"[AzureBoardService-DEBUG] read_feature: GET {url} status={response.status_code}")
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
                print(f"[AzureBoardService-DEBUG] read_feature: Falha ao buscar feature. status={response.status_code}, body={response.text}")
                return {
                    'error': response.text,
                    'status_code': response.status_code
                }
        except Exception as e:
            print(f"[AzureBoardService-DEBUG] read_feature: Exceção ao buscar feature: {str(e)}")
            return {
                'error': str(e)
            }

    def create_tasks_from_feature(self, feature_id: str, markdown_table: str) -> List[Dict[str, Any]]:
        if not feature_id or not markdown_table or not isinstance(markdown_table, str) or len(markdown_table.strip()) == 0:
            print(f"[AzureBoardService-DEBUG] ERRO: feature_id ou markdown_table inválidos. feature_id={feature_id}, len(markdown_table)={len(markdown_table) if markdown_table else 0}")
            raise ValueError(f"[AzureBoardService] ERRO: feature_id ou markdown_table inválidos. feature_id={feature_id}, len(markdown_table)={len(markdown_table) if markdown_table else 0}")
        print(f"[AzureBoardService-DEBUG] Chamando TaskParserService.parse_tasks_from_markdown")
        parser = TaskParserService()
        tasks = parser.parse_tasks_from_markdown(markdown_table)
        print(f"[AzureBoardService-DEBUG] Parsing concluído. Total de tarefas parseadas: {len(tasks)}")
        if len(tasks) == 0:
            print(f"[AzureBoardService-WARNING] Nenhuma tarefa foi parseada da tabela Markdown. Verifique o formato da tabela.")
            return [{"error": "Nenhuma tarefa foi encontrada no relatório para criar na feature."}]
        token = self._get_token()
        created_tasks = []
        total_tasks = len(tasks)
        parent_feature_url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/workitems/{feature_id}"
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
                    "url": parent_feature_url,
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

    def create_tasks_from_report(self, feature_id: str, markdown_table: str) -> List[Dict[str, Any]]:
        if not feature_id or not markdown_table or not isinstance(markdown_table, str) or len(markdown_table.strip()) == 0:
            print(f"[AzureBoardService-DEBUG] ERRO: feature_id ou markdown_table inválidos. feature_id={feature_id}, len(markdown_table)={len(markdown_table) if markdown_table else 0}")
            raise ValueError(f"[AzureBoardService] ERRO: feature_id ou markdown_table inválidos. feature_id={feature_id}, len(markdown_table)={len(markdown_table) if markdown_table else 0}")
        print(f"[AzureBoardService-DEBUG] Chamando AzureBoardService.create_tasks_from_feature com feature_id={feature_id}")
        created_tasks = self.create_tasks_from_feature(feature_id, markdown_table)
        return created_tasks

    def _basic_auth_header(self, token):
        import base64
        return base64.b64encode(f':{token}'.encode('utf-8')).decode('utf-8')

    # ... demais funções permanecem inalteradas ...
