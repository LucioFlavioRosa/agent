import os
from openai import OpenAI
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

from domain.interfaces.rag_retriever_interface import IRAGRetriever

class AzureAISearchRAGRetriever(IRAGRetriever):
    
    def __init__(self):
        key_vault_url = os.environ["KEY_VAULT_URL"]
        credential = DefaultAzureCredential()
        secret_client = SecretClient(vault_url=key_vault_url, credential=credential)

        openai_api_key = secret_client.get_secret("openaiapi").value
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.embedding_model_name = os.environ["AZURE_OPENAI_EMBEDDING_MODEL_NAME"]

        ai_search_endpoint = os.environ["AI_SEARCH_ENDPOINT"]
        ai_search_api_key = secret_client.get_secret("aisearchapi").value
        ai_search_index_name = os.environ["AI_SEARCH_INDEX_NAME"]

        self.search_client = SearchClient(
            endpoint=ai_search_endpoint,
            index_name=ai_search_index_name,
            credential=AzureKeyCredential(ai_search_api_key)
        )

    def buscar_politicas(self, query: str, top_k: int = 5) -> str:
        try:
            print(f"[RAG Retriever] Gerando embedding para a consulta: '{query}'")
            response = self.openai_client.embeddings.create(
                model=self.embedding_model_name,
                input=query
            )
            query_vector = response.data[0].embedding

            vector_query = VectorizedQuery(vector=query_vector, k_nearest_neighbors=top_k, fields="content_vector")

            print(f"[RAG Retriever] Buscando as {top_k} políticas mais relevantes...")
            results = self.search_client.search(
                search_text="",
                vector_queries=[vector_query],
                select=["content", "source_file", "heading"]
            )

            contexto_formatado = []
            for result in results:
                fonte = result.get('source_file', 'Documento Desconhecido')
                secao = result.get('heading', 'Seção não especificada')
                contexto_formatado.append(
                    f"--- Início da Política (Fonte: {fonte}, Seção: {secao}) ---\n"
                    f"{result['content']}\n"
                    f"--- Fim da Política ---\n"
                )

            if not contexto_formatado:
                print("[RAG Retriever] Nenhuma política relevante encontrada.")
                return "Nenhuma política específica foi encontrada para esta análise."

            print(f"[RAG Retriever] {len(contexto_formatado)} trechos de políticas encontrados e formatados.")
            return "\n".join(contexto_formatado)

        except Exception as e:
            print(f"ERRO no RAG Retriever: Falha ao buscar políticas. Causa: {e}")
            return "Ocorreu um erro ao tentar buscar as políticas de desenvolvimento."