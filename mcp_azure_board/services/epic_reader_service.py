import requests
from typing import Optional

class EpicReaderService:
    @staticmethod
    def get_epic_title(epic_id: str, organization: str, project: str) -> Optional[str]:
        try:
            token = None
            from tools.azure_secret_manager import AzureSecretManager
            secret_manager = AzureSecretManager()
            token = secret_manager.get_secret(f"azure-token-{organization}")
            url = f"https://dev.azure.com/{organization}/{project}/_apis/wit/workitems/{epic_id}?api-version=7.1-preview.3"
            import base64
            auth_header = base64.b64encode(f':{token}'.encode('utf-8')).decode('utf-8')
            headers = {
                'Authorization': f'Basic {auth_header}'
            }
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                fields = data.get('fields', {})
                return fields.get('System.Title')
            return None
        except Exception:
            return None
