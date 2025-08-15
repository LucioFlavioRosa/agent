# Arquivo: tools/requisicao_openai.py (ou seu equivalente)

import os
from openai import OpenAI
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from typing import Optional, Dict, Any

# Importe as interfaces necessárias
from domain.interfaces.llm_provider_interface import ILLMProvider
from domain.interfaces.rag_retriever_interface import IRAGRetriever

class OpenAILLMProvider(ILLMProvider):
    """
    Implementação flexível que adapta os parâmetros da API da OpenAI
    com base no nome do modelo fornecido.
    """
    def __init__(self, rag_retriever: Optional[IRAGRetriever] = None):
        self.rag_retriever = rag_retriever

        key_vault_url = os.environ["KEY_VAULT_URL"]
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=key_vault_url, credential=credential)
        self.OPENAI_API_KEY = client.get_secret("openaiapi").value
        if not self.OPENAI_API_KEY:
            raise ValueError("A chave da API da OpenAI não foi encontrada.")
        self.openai_client = OpenAI(api_key=self.OPENAI_API_KEY)
        
        # --- MUDANÇA: Define um modelo padrão caso nenhum seja fornecido ---
        self.DEFAULT_MODEL = "gpt-4o" # Use um modelo moderno como padrão

    def carregar_prompt(self, tipo_analise: str) -> str:
        caminho_prompt = os.path.join(os.path.dirname(__file__), 'prompts', f'{tipo_analise}.md')
        try:
            with open(caminho_prompt, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise ValueError(f"Arquivo de prompt para '{tipo_analise}' não encontrado: {caminho_prompt}")

    def _construir_parametros_api(self, model_name: str, max_token_out: int) -> Dict[str, Any]:
        """
        Cria o dicionário de parâmetros de forma condicional baseado no nome do modelo.
        """
        # Converte para minúsculas para uma comparação robusta
        model_lower = model_name.lower()
        
        # --- MUDANÇA: Lógica de decisão ---
        if "gpt-5" in model_lower:
            print(f"[OpenAI Handler] Usando parâmetros para modelo legado: '{model_name}'")
            return {
                "max_completion_tokens": max_token_out,
            }
            
        else:
            print(f"[OpenAI Handler] Usando parâmetros para modelo moderno: '{model_name}'")
            # Modelos modernos geralmente não precisam de 'temperature' para tarefas determinísticas
            return {
                "max_tokens": max_token_out
                "temperature": 0.3
            }

    def executar_analise_llm(
        self,
        tipo_analise: str,
        codigo: str,
        analise_extra: str,
        usar_rag: bool,
        model_name: Optional[str], # Agora pode ser nulo
        max_token_out: int
    ) -> dict:
        prompt_sistema_base = self.carregar_prompt(tipo_analise)
        prompt_sistema_final = prompt_sistema_base

        if usar_rag and self.rag_retriever:
            # Lógica do RAG (inalterada)
            # ...
            pass # Apenas para o exemplo, mantenha sua lógica de RAG aqui

        mensagens = [
            {"role": "system", "content": prompt_sistema_final},
            {'role': 'user', 'content': codigo},
            {'role': 'user',
             'content': f'Instruções extras do usuário: {analise_extra}' if analise_extra.strip() else 'Nenhuma instrução extra.'}
        ]

        # --- MUDANÇA: Usa o modelo do payload ou o padrão da classe ---
        modelo_final = model_name or self.DEFAULT_MODEL
        
        # --- MUDANÇA: Constrói os parâmetros dinamicamente ---
        parametros_api = self._construir_parametros_api(modelo_final, max_token_out)

        try:
            response = self.openai_client.chat.completions.create(
                model=modelo_final,
                messages=mensagens,
                **parametros_api
            )
            conteudo_resposta = response.choices[0].message.content.strip()
            return {
                'reposta_final': conteudo_resposta,
                'tokens_entrada': response.usage.prompt_tokens,
                'tokens_saida': response.usage.completion_tokens
            }
        except Exception as e:
            print(f"ERRO: Falha na chamada à API da OpenAI para análise '{tipo_analise}'. Causa: {e}")
            raise RuntimeError(f"Erro ao comunicar com a OpenAI: {e}") from e
