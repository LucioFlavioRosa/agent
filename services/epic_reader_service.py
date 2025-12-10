import requests

class EpicReaderService:
    @staticmethod
    def get_epic_title(epic_id: str, organization: str, project: str) -> str:
        from tools.azure_secret_manager import AzureSecretManager
        secret_manager = AzureSecretManager()
        token_secret_name = f"azure-token-{organization}" if organization else "azure-token"
        try:
            token = secret_manager.get_secret(token_secret_name)
        except Exception:
            token = secret_manager.get_secret("azure-token")
        import base64
        basic_auth = base64.b64encode(f':{token}'.encode('utf-8')).decode('utf-8')
        url = f"https://dev.azure.com/{organization}/{project}/_apis/wit/workitems/{epic_id}?api-version=7.1-preview.3"
        headers = {
            'Authorization': f'Basic {basic_auth}'
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            fields = data.get('fields', {})
            return fields.get('System.Title', '')
        return ''
