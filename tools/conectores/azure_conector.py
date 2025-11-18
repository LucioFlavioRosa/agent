import requests
from .base_conector import safe_requests_get

class AzureConector:
    def __init__(self, token):
        self.token = token

    def get_resource_info(self, resource_url):
        headers = {'Authorization': f'Bearer {self.token}'}
        response = safe_requests_get(requests, resource_url, headers=headers)
        response.raise_for_status()
        return response.json()
