import requests
from .base_conector import safe_requests_get

class GithubConector:
    def __init__(self, token):
        self.token = token

    def get_repo_info(self, repo_url):
        # Usa safe_requests_get para proteger contra SSRF
        headers = {'Authorization': f'token {self.token}'}
        response = safe_requests_get(requests, repo_url, headers=headers)
        response.raise_for_status()
        return response.json()
