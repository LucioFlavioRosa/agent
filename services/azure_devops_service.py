import requests
import base64

class AzureDevOpsService:
    def __init__(self):
        pass

    def create_epic(self, organization, project, board, title, description, token):
        url = f"https://dev.azure.com/{organization}/{project}/_apis/wit/workitems/$Epic?api-version=7.1"
        headers = {
            "Content-Type": "application/json-patch+json",
            "Authorization": f"Basic {base64.b64encode(f':{token}'.encode()).decode()}"
        }
        payload = [
            {"op": "add", "path": "/fields/System.Title", "value": title},
            {"op": "add", "path": "/fields/System.Description", "value": description},
            {"op": "add", "path": "/fields/System.AreaPath", "value": board},
            {"op": "add", "path": "/fields/System.IterationPath", "value": board}
        ]
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            epic_id = data.get('id')
            epic_url = data.get('url')
            return {"epic_id": epic_id, "epic_url": epic_url}
        except Exception as e:
            print(f"[AzureDevOpsService] Erro ao criar épico: {e}")
            raise
