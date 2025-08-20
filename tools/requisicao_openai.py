import os
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from typing import Optional, Dict, Any

from domain.interfaces.llm_provider_interface import ILLMProvider
from domain.interfaces.rag_retriever_interface import IRAGRetriever

class OpenAILLMProvider(ILLMProvider):
    """
    Implementação que se conecta ao Azure OpenAI Service, usando deployments
    de modelos provisionados pelo usuário.
    """
    def __init__(self, rag_retriever: Optional[IRAGRetriever] = None):
        self.rag_retriever = rag_retriever
        
        try:
            self.azure_endpoint = os.environ["AZURE_OPENAI_MODELS"]
            
            key_vault_url = os.environ["KEY_VAULT_URL"]
            credential = DefaultAzureCredential()
            secret_client = SecretClient(vault_url=key_vault_url, credential=credential)
            
            api_key = secret_client.get_secret("azure-openai-modelos").value
            if not api_key:
                raise ValueError("A chave da API do Azure OpenAI não foi encontrada no segredo 'azure-openai-api-key'.")
            
            self.openai_client = AzureOpenAI(
                azure_endpoint=self.azure_endpoint,
                api_version="2025-03-01-preview",
                api_key=api_key,
            )

        except KeyError as e:
            raise EnvironmentError(f"ERRO: A variável de ambiente {e} não foi configurada para o Azure OpenAI.")
        except Exception as e:
            print(f"ERRO CRÍTICO ao configurar o cliente do Azure OpenAI: {e}")
            raise

    def carregar_prompt(self, tipo_tarefa: str) -> str:
        caminho_prompt = os.path.join(os.path.dirname(__file__), 'prompts', f'{tipo_tarefa}.md')
        try:
            with open(caminho_prompt, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise ValueError(f"Arquivo de prompt para '{tipo_analise}' não encontrado: {caminho_prompt}")
            
    def executar_prompt(
        self,
        tipo_tarefa: str,
        prompt_principal: str,
        instrucoes_extras: str,
        usar_rag: bool,
        model_name: Optional[str],
        max_token_out: int
    ) -> dict:

        modelo_final = model_name or os.environ.get("AZURE_DEFAULT_DEPLOYMENT_NAME")
        model_lower = modelo_final.lower()

        prompt_sistema_base = self.carregar_prompt(tipo_tarefa)
        prompt_sistema_final = prompt_sistema_base

        if usar_rag and self.rag_retriever:
           
            politicas_relevantes = self.rag_retriever.buscar_politicas(
                query=f"políticas de {tipo_analise} para desenvolvimento de software"
            )
            prompt_sistema_final = ( # Atualiza a variável final com o contexto
                f"{prompt_sistema_base}\n\n"
                "--- POLÍTICAS RELEVANTES DA EMPRESA (CONTEXTO RAG) ---\n"
                f"{politicas_relevantes}"
            )
        
        try:
            mensagens = [
                    {"role": "system", "content": prompt_sistema_final},
                    {'role': 'user', 'content': prompt_principal},
                    {'role': 'user',
                     'content': f'Instruções extras do usuário: {instrucoes_extras}' if analise_extra.strip() else 'Nenhuma instrução extra.'}
                ]
                
            response = self.openai_client.chat.completions.create(
                    model=modelo_final,
                    messages=mensagens,
                    temperature=0.3,
                    max_completion_tokens=max_token_out
                )

            conteudo_resposta = (response.choices[0].message.content or "").strip()
            tokens_entrada = response.usage.prompt_tokens
            tokens_saida = response.usage.completion_tokens

            return {
                'reposta_final': conteudo_resposta,
                'tokens_entrada': tokens_entrada,
                'tokens_saida': tokens_saida
            }
            
        except Exception as e:
            print(f"ERRO: Falha na chamada à API da OpenAI para o modelo '{modelo_final}'. Causa: {e}")
            raise RuntimeError(f"Erro ao comunicar com a OpenAI: {e}") from e
