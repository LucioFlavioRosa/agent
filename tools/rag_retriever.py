# Arquivo: tools/rag_retriever.py
import os
from openai import OpenAI
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

# Cliente do Key Vault para buscar segredos
key_vault_url = os.environ["KEY_VAULT_URL"]
credential = DefaultAzureCredential()
secret_client = SecretClient(vault_url=key_vault_url, credential=credential)

# Cliente da OpenAI (usado aqui para gerar o embedding da pergunta)
OPENAI_API_KEY = secret_client.get_secret("openaiapi").value
openai_client = OpenAI(api_key=OPENAI_API_KEY)
AZURE_OPENAI_EMBEDDING_MODEL_NAME = os.environ["AZURE_OPENAI_EMBEDDING_MODEL_NAME"] # ex: "text-embedding-ada-002"

# Cliente do Azure AI Search
AI_SEARCH_ENDPOINT = os.environ["AI_SEARCH_ENDPOINT"]
AI_SEARCH_API_KEY = secret_client.get_secret("aisearchapi").value
AI_SEARCH_INDEX_NAME = os.environ["AI_SEARCH_INDEX_NAME"]

def buscar_politicas_relevantes(query: str, top_k: int = 10) -> str:
    """
    Busca em um índice do Azure AI Search por políticas relevantes para uma consulta,
    usando busca vetorial.

    Args:
        query (str): O termo de busca (ex: "Padrões de Pull Request em Python").
        top_k (int): O número de documentos mais relevantes a serem retornados.

    Returns:
        str: Uma string formatada contendo os trechos das políticas encontradas.
    """
    try:
        search_client = SearchClient(
            endpoint=AI_SEARCH_ENDPOINT,
            index_name=AI_SEARCH_INDEX_NAME,
            credential=AzureKeyCredential(AI_SEARCH_API_KEY)
        )

        print(f"[RAG Retriever] Gerando embedding para a consulta: '{query}'")
        # 1. Vetoriza a pergunta do usuário para a busca
        response = openai_client.embeddings.create(
            model=AZURE_OPENAI_EMBEDDING_MODEL_NAME,
            input=query
        )
        query_vector = response.data[0].embedding

        # 2. Prepara a consulta vetorial para o Azure AI Search
        vector_query = VectorizedQuery(vector=query_vector, k_nearest_neighbors=top_k, fields="content_vector")

        print(f"[RAG Retriever] Buscando as {top_k} políticas mais relevantes...")
        results = search_client.search(
            search_text="", # Pode adicionar busca de texto aqui para uma busca híbrida
            vector_queries=[vector_query],
            select=["content", "source_file", "heading"] # Seleciona os campos que queremos de volta
        )

        # 3. Formata os resultados em um contexto de texto claro
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
