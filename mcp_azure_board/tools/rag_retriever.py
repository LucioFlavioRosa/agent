from typing import Any

class AzureAISearchRAGRetriever:
    def __init__(self, search_service_name: str = None, index_name: str = None, api_key: str = None):
        self.search_service_name = search_service_name
        self.index_name = index_name
        self.api_key = api_key
    def buscar_politicas(self, query: str) -> Any:
        return ""
