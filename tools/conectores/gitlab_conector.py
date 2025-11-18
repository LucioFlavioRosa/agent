import requests
from .base_conector import safe_requests_get

class GitlabConector:
    def __init__(self, token):
        self.token = token

    def get_project_info(self, project_url):
        headers = {'Private-Token': self.token}
        response = safe_requests_get(requests, project_url, headers=headers)
        response.raise_for_status()
        return response.json()
