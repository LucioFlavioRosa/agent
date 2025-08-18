import anthropic
from typing import Optional, Dict, Any

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

from domain.interfaces.llm_provider_interface import ILLMProvider
from domain.interfaces.rag_retriever_interface import IRAGRetriever

class AnthropicClaudeProvider(ILLMProvider):
    """
    Implementação de ILLMProvider para a API do Claude da Anthropic,
    com busca segura de credenciais via Azure Key Vault.
    """
    def __init__(self, rag_retriever: Optional[IRAGRetriever] = None):
        self.rag_retriever = rag_retriever
        
        # --- LÓGICA DE INICIALIZAÇÃO CORRIGIDA E PADRONIZADA ---
        print("Configurando o cliente da Anthropic (Claude)...")
        try:
            key_vault_url = os.environ["KEY_VAULT_URL"]
            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=key_vault_url, credential=credential)
            
            # Busca o segredo específico da Anthropic no Key Vault
            anthropic_api_key = client.get_secret("ANTHROPICAPIKEY").value
            if not anthropic_api_key:
                raise ValueError("A chave da API da Anthropic não foi encontrada no segredo 'anthropicapi' do Key Vault.")
            
            self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
            print("Cliente da Anthropic (Claude) configurado com sucesso via Key Vault.")

        except KeyError:
            # Captura o erro se a variável de ambiente KEY_VAULT_URL não existir
            raise EnvironmentError("ERRO: A variável de ambiente KEY_VAULT_URL não foi configurada.")
        except Exception as e:
            # Captura outras exceções (ex: segredo não encontrado, permissão negada)
            print(f"ERRO CRÍTICO ao configurar o cliente da Anthropic: {e}")
            raise

    def carregar_prompt(self, tipo_analise: str) -> str:
        # (Esta função não muda)
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
    ) -> Dict[str, Any]:
        
        modelo_final = model_name or "claude-3-opus-20240229" # Modelo padrão do Claude
        
        prompt_sistema = self.carregar_prompt(tipo_analise)

        if usar_rag and self.rag_retriever:
            print("[Claude Handler] Usando o RAG retriever injetado...")
            politicas_relevantes = self.rag_retriever.buscar_politicas(
                query=f"políticas de {tipo_analise} para desenvolvimento de software"
            )
            prompt_sistema = f"{prompt_sistema}\n\n--- CONTEXTO ADICIONAL ---\n{politicas_relevantes}"

        # A API do Claude tem uma estrutura de mensagens ligeiramente diferente
        mensagens = [
            {"role": "user", "content": f"--- CÓDIGO PARA ANÁLISE ---\n{codigo}"},
        ]
        if analise_extra.strip():
            mensagens.append({"role": "user", "content": f"--- INSTRUÇÕES EXTRAS ---\n{analise_extra}"})

        try:
            print(f"[Claude Handler] Chamando o modelo: '{modelo_final}'")
            
            response = self.anthropic_client.messages.create(
                model=modelo_final,
                system=prompt_sistema,  
                messages=mensagens,
                max_tokens=max_token_out,
                temperature=0.3
            )
            
            conteudo_resposta = response.content[0].text
            
            # O contrato exige que retornemos um dicionário específico
            return {
                'reposta_final': conteudo_resposta,
                'tokens_entrada': response.usage.input_tokens,
                'tokens_saida': response.usage.output_tokens
            }
            
        except Exception as e:
            print(f"ERRO: Falha na chamada à API da Anthropic para análise '{tipo_analise}'. Causa: {e}")
            raise RuntimeError(f"Erro ao comunicar com a API da Anthropic: {e}") from e
