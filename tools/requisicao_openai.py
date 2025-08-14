# Arquivo de implementação do OpenAI (VERSÃO REVISADA)

import os
from openai import OpenAI
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from typing import Optional

# Importe as interfaces necessárias
from domain.interfaces.llm_provider_interface import ILLMProvider
from domain.interfaces.rag_retriever_interface import IRAGRetriever # <-- NOVA IMPORTAÇÃO

class OpenAILLMProvider(ILLMProvider):
    """
    Implementação que agora pode receber um RAG Retriever opcional.
    """
    def __init__(self, rag_retriever: Optional[IRAGRetriever] = None):
        # O RAG Retriever agora é INJETADO!
        self.rag_retriever = rag_retriever

        # O resto da inicialização continua igual...
        key_vault_url = os.environ["KEY_VAULT_URL"]
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=key_vault_url, credential=credential)
        self.OPENAI_API_KEY = client.get_secret("openaiapi").value
        if not self.OPENAI_API_KEY:
            raise ValueError("A chave da API da OpenAI não foi encontrada.")
        self.openai_client = OpenAI(api_key=self.OPENAI_API_KEY)

    def carregar_prompt(self, tipo_analise: str) -> str:
        # ... (código inalterado) ...
        caminho_prompt = os.path.join(os.path.dirname(__file__), 'prompts', f'{tipo_analise}.md')
        try:
            with open(caminho_prompt, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise ValueError(f"Arquivo de prompt para a análise '{tipo_analise}' não encontrado em: {caminho_prompt}")


    def executar_analise_llm(
        self,
        tipo_analise: str,
        codigo: str,
        analise_extra: str,
        usar_rag: bool,
        model_name: str,
        max_token_out: int
    ) -> dict:
        prompt_sistema_base = self.carregar_prompt(tipo_analise)
        prompt_sistema_final = prompt_sistema_base

        # A lógica agora usa o retriever injetado!
        if usar_rag and self.rag_retriever:
            print("[OpenAI Handler] Flag 'usar_rag' é True. Usando o RAG retriever injetado...")
            politicas_relevantes = self.rag_retriever.buscar_politicas(
                query=f"políticas de {tipo_analise} para desenvolvimento de software"
            )
            prompt_sistema_final = (
                f"{prompt_sistema_base}\n\n"
                "--- POLÍTICAS RELEVANTES DA EMPRESA ---\n"
                "Você DEVE, obrigatoriamente, basear sua análise e sugestões nas políticas da empresa descritas abaixo. "
                "Para cada sugestão de mudança que você fizer, adicione uma chave 'politica_referenciada' "
                "indicando a 'Fonte' e 'Seção' da política que justifica a mudança.\n\n"
                f"{politicas_relevantes}"
            )
        else:
            print("[OpenAI Handler] 'usar_rag' é False ou nenhum retriever foi fornecido. Análise prosseguirá sem RAG.")
        
        # ... (o resto da função, com a chamada para a API da OpenAI, continua exatamente igual) ...
        mensagens = [
            {"role": "system", "content": prompt_sistema_final},
            {'role': 'user', 'content': codigo},
            {'role': 'user',
             'content': f'Instruções extras do usuário: {analise_extra}' if analise_extra.strip() else 'Nenhuma instrução extra.'}
        ]
        try:
            response = self.openai_client.chat.completions.create(
                model=model_name,
                messages=mensagens,
                temperature=0.3,
                max_completion_tokens=max_token_out
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
