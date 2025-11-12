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
                title = fields.get('System.Title')
                description = fields.get('System.Description')
                acceptance_criteria = fields.get('Microsoft.VSTS.Common.AcceptanceCriteria')
                print(f"[AzureBoardService-DEBUG] read_feature: title={title}, description={description}, acceptance_criteria={acceptance_criteria}")
                if not title or not description or not acceptance_criteria:
                    print(f"[AzureBoardService-ERROR] Campos obrigatórios ausentes na feature: title={title}, description={description}, acceptance_criteria={acceptance_criteria}")
                return {
                    'id': data.get('id'),
                    'title': title,
                    'description': description,
                    'acceptance_criteria': acceptance_criteria,
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
    # ... resto do código permanece igual ...
