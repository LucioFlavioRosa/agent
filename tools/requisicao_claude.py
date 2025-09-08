import os
import uuid
import anthropic
from datetime import datetime
from typing import Optional, Dict, Any

from domain.interfaces.llm_provider_interface import ILLMProviderComplete
from domain.interfaces.rag_retriever_interface import IRAGRetriever
from domain.interfaces.secret_manager_interface import ISecretManager
from tools.azure_secret_manager import AzureSecretManager
from tools.azure_table_logger import log_tokens_async

class AnthropicClaudeProvider(ILLMProviderComplete):
    def __init__(self, rag_retriever: Optional[IRAGRetriever] = None, secret_manager: ISecretManager = None):
        self.rag_retriever = rag_retriever
        self.secret_manager = secret_manager or AzureSecretManager()
        
        print("Configurando o cliente da Anthropic (Claude)...")
        try:
            anthropic_api_key = self.secret_manager.get_secret("ANTHROPICAPIKEY")
            self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
            print("Cliente da Anthropic (Claude) configurado com sucesso.")
        except Exception as e:
            print(f"ERRO CRÍTICO ao configurar o cliente da Anthropic: {e}")
            raise

    def carregar_prompt(self, tipo_tarefa: str) -> str:
        caminho_prompt = os.path.join(os.path.dirname(__file__), 'prompts', f'{tipo_tarefa}.md')
        try:
            with open(caminho_prompt, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise ValueError(f"Arquivo de prompt para '{tipo_tarefa}' não encontrado: {caminho_prompt}")

    def executar_prompt(
        self,
        tipo_tarefa: str,
        prompt_principal: str,
        instrucoes_extras: str = "",
        usar_rag: bool = False,
        model_name: Optional[str] = None,
        max_token_out: int = 15000
    ) -> Dict[str, Any]:
        modelo_final = model_name or "claude-3-opus-20240229"
        job_id = str(uuid.uuid4())
        
        prompt_sistema = self.carregar_prompt(tipo_tarefa)

        if usar_rag and self.rag_retriever:
            print("[Claude Handler] Usando o RAG retriever injetado...")
            politicas_relevantes = self.rag_retriever.buscar_politicas(
                query=f"políticas de {tipo_tarefa} para desenvolvimento de software"
            )
            prompt_sistema = f"{prompt_sistema}\n\n--- CONTEXTO ADICIONAL ---\n{politicas_relevantes}"

        mensagens = [
            {"role": "user", "content": f"--- CÓDIGO PARA ANÁLISE ---\n{prompt_principal}"},
        ]
        if instrucoes_extras.strip():
            mensagens.append({"role": "user", "content": f"--- INSTRUÇÕES EXTRAS ---\n{instrucoes_extras}"})

        try:
            print(f"[Claude Handler] Chamando o modelo: '{modelo_final}'")
            
            response = self.anthropic_client.messages.create(
                model=modelo_final,
                system=prompt_sistema,  
                messages=mensagens,
                max_tokens=max_token_out,
                temperature=0.3,
                timeout=900.0
            )
            
            conteudo_resposta = response.content[0].text
            tokens_entrada = response.usage.input_tokens
            tokens_saida = response.usage.output_tokens
            
            projeto = model_name or "claude"
            data_atual = datetime.utcnow().strftime("%Y-%m-%d")
            hora_atual = datetime.utcnow().strftime("%H:%M:%S")
            
            log_tokens_async(
                projeto=projeto,
                analysis_type=tipo_tarefa,
                llm_model=modelo_final,
                tokens_in=tokens_entrada,
                tokens_out=tokens_saida,
                data=data_atual,
                hora=hora_atual,
                status_update="completed",
                job_id=job_id
            )
            
            return {
                'reposta_final': conteudo_resposta,
                'tokens_entrada': tokens_entrada,
                'tokens_saida': tokens_saida
            }
            
        except Exception as e:
            print(f"ERRO: Falha na chamada à API da Anthropic para análise '{tipo_tarefa}'. Causa: {e}")
            raise RuntimeError(f"Erro ao comunicar com a API da Anthropic: {e}") from e
    
    def executar_prompt_com_rag(
        self,
        tipo_tarefa: str,
        prompt_principal: str,
        instrucoes_extras: str = "",
        usar_rag: bool = False,
        max_token_out: int = 15000
    ) -> Dict[str, Any]:
        return self.executar_prompt(
            tipo_tarefa=tipo_tarefa,
            prompt_principal=prompt_principal,
            instrucoes_extras=instrucoes_extras,
            usar_rag=usar_rag,
            max_token_out=max_token_out
        )
    
    def executar_prompt_com_modelo(
        self,
        tipo_tarefa: str,
        prompt_principal: str,
        instrucoes_extras: str = "",
        model_name: Optional[str] = None,
        max_token_out: int = 15000
    ) -> Dict[str, Any]:
        return self.executar_prompt(
            tipo_tarefa=tipo_tarefa,
            prompt_principal=prompt_principal,
            instrucoes_extras=instrucoes_extras,
            model_name=model_name,
            max_token_out=max_token_out
        )