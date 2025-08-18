# Arquivo: tools/requisicao_openai.py (VERSÃO FINAL COMPLETA)

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
    Implementação flexível que adapta a chamada à API da OpenAI com base no
    modelo e suporta enriquecimento de prompt via RAG.
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
        self.DEFAULT_MODEL = "gpt-4o"

    def carregar_prompt(self, tipo_analise: str) -> str:
        """
        Carrega o conteúdo do arquivo de prompt correspondente.
        """
        caminho_prompt = os.path.join(os.path.dirname(__file__), 'prompts', f'{tipo_analise}.md')
        try:
            with open(caminho_prompt, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise ValueError(f"Arquivo de prompt para '{tipo_analise}' não encontrado: {caminho_prompt}")

    def executar_analise_llm(
        self,
        tipo_analise: str,
        codigo: str,
        analise_extra: str,
        usar_rag: bool,
        model_name: Optional[str],
        max_token_out: int
    ) -> dict:
        
        modelo_final = model_name or self.DEFAULT_MODEL
        model_lower = modelo_final.lower()
        
        prompt_sistema_base = self.carregar_prompt(tipo_analise)
        prompt_sistema_final = prompt_sistema_base

        # Lógica do RAG para enriquecer o prompt antes da chamada
        if usar_rag and self.rag_retriever:
            print("[OpenAI Handler] Flag 'usar_rag' é True. Buscando políticas relevantes...")
            politicas_relevantes = self.rag_retriever.buscar_politicas(
                query=f"políticas de {tipo_analise} para desenvolvimento de software"
            )
            prompt_sistema_final = (
                f"{prompt_sistema_base}\n\n"
                "--- POLÍTICAS RELEVANTES DA EMPRESA (CONTEXTO RAG) ---\n"
                "Você DEVE, obrigatoriamente, basear sua análise e sugestões nas políticas da empresa descritas abaixo. "
                "Para cada sugestão de mudança que você fizer, adicione uma chave 'politica_referenciada' "
                "indicando a 'Fonte' e 'Seção' da política que justifica a mudança.\n\n"
                f"{politicas_relevantes}"
            )
        else:
            pass

        try:
            if "gpt-5" in model_lower:
                # --- BLOCO PARA A NOVA API (HIPOTÉTICA) ---
                print("[OpenAI Handler] Usando a nova interface de API (client.responses.create)")
                
                prompt_combinado = f"{prompt_sistema_final}\n\n--- CÓDIGO ---\n{codigo}\n\n--- INSTRUÇÕES EXTRAS ---\n{analise_extra}"
                
                # A chamada usa a nova estrutura que você descreveu
                response = self.openai_client.responses.create(
                    model=modelo_final,
                    input=prompt_combinado,
                    reasoning={"effort": "high"},
                    text={"verbosity": "high"}
                )
                
                # Adapta a resposta para o formato que nosso sistema espera
                conteudo_resposta = response.output_text
                tokens_entrada = response.usage.input_tokens
                tokens_saida = response.usage.output_tokens

            else:
                
                mensagens = [
                    {"role": "system", "content": prompt_sistema_final},
                    {'role': 'user', 'content': codigo},
                    {'role': 'user',
                     'content': f'Instruções extras do usuário: {analise_extra}' if analise_extra.strip() else 'Nenhuma instrução extra.'}
                ]
                
                response = self.openai_client.chat.completions.create(
                    model=modelo_final,
                    messages=mensagens,
                    temperature=0.3,
                    max_tokens=max_token_out
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
