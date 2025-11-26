import os
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

class AzureAISearchRAGRetriever:
    def __init__(self, endpoint=None, index_name=None, api_key=None):
        self.endpoint = endpoint or os.getenv("AZURE_SEARCH_ENDPOINT")
        self.index_name = index_name or os.getenv("AZURE_SEARCH_INDEX_NAME")
        self.api_key = api_key or os.getenv("AZURE_SEARCH_API_KEY")
        if not self.endpoint or not self.index_name or not self.api_key:
            raise ValueError("Configuração do Azure Search incompleta.")
        self.client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=AzureKeyCredential(self.api_key)
        )

    def retrieve(self, query, top=5):
        results = self.client.search(search_text=query, top=top)
        return [doc for doc in results]
