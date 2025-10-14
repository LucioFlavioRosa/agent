import requests

class AzureRepositoryWrapper:
    def __init__(self, organization, project, pat, repo_data):
        self._organization = organization
        self._project = project
        self._provider_type = 'azure_devops'
        self.id = repo_data.get('id')
        self.name = repo_data.get('name')
        self._repository = repo_data.get('name')
        self._repo_data = repo_data

class AzureRepositoryProvider:
    def __init__(self, organization, project, pat):
        self.organization = organization
        self.project = project
        self.pat = pat
        self._base_url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories"
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {self._encode_pat(pat)}"
        }

    def _encode_pat(self, pat):
        import base64
        return base64.b64encode(f':{pat}'.encode()).decode()

    def get_repository(self, repo_name):
        url = f"{self._base_url}/{repo_name}?api-version=7.0"
        response = requests.get(url, headers=self._headers, timeout=30)
        response.raise_for_status()
        repo_data = response.json()
        wrapper = AzureRepositoryWrapper(self.organization, self.project, self.pat, repo_data)
        return wrapper

    def get_repository_id(self, repo_name):
        url = f"{self._base_url}/{repo_name}?api-version=7.0"
        response = requests.get(url, headers=self._headers, timeout=30)
        response.raise_for_status()
        repo_data = response.json()
        return repo_data.get('id')
