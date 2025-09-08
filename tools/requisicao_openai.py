import os
import uuid
from datetime import datetime
from openai import AzureOpenAI
from typing import Optional, Dict, Any

from domain.interfaces.llm_provider_interface import ILLMProviderComplete
from domain.interfaces.rag_retriever_interface import IRAGRetriever
from domain.interfaces.secret_manager_interface import ISecretManager
from tools.azure_secret_manager import AzureSecretManager
from tools.azure_table_logger import log_tokens_async

class OpenAILLMProvider(ILLMProviderComplete):
    def __init__(self, rag_retriever: Optional[IRAGRetriever] = None, secret_manager: ISecretManager = None):
        self.rag_retriever = rag_retriever
        self.secret_manager = secret_manager or AzureSecretManager()
        
        try:
            self.azure_endpoint = os.environ["AZURE_OPENAI_MODELS"]
            
            api_key = self.secret_manager.get_secret("azure-openai-modelos")
            
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
            raise ValueError(f"Arquivo de prompt para '{tipo_tarefa}' não encontrado: {caminho_prompt}")
    
    def executar_prompt(
        self,
        tipo_tarefa: str,
        prompt_principal: str,
        instrucoes_extras: str = "",
        usar_rag: bool = False,
        model_name: Optional[str] = None,
        max_token_out: int = 15000,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        modelo_final = model_name or os.environ.get("AZURE_DEFAULT_DEPLOYMENT_NAME")
        job_id_final = job_id or str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        prompt_sistema_base = self.carregar_prompt(tipo_tarefa)
        prompt_sistema_final = prompt_sistema_base

        if usar_rag and self.rag_retriever:
            politicas_relevantes = self.rag_retriever.buscar_politicas(
                query=f"políticas de {tipo_tarefa} para desenvolvimento de software"
            )
            prompt_sistema_final = (
                f"{prompt_sistema_base}\n\n"
                "--- POLÍTICAS RELEVANTES DA EMPRESA (CONTEXTO RAG) ---\n"
                f"{politicas_relevantes}"
            )
        
        try:
            mensagens = [
                {"role": "system", "content": prompt_sistema_final},
                {'role': 'user', 'content': prompt_principal},
                {'role': 'user',
                 'content': f'Instruções extras do usuário: {instrucoes_extras}' if instrucoes_extras.strip() else 'Nenhuma instrução extra.'}
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

            projeto = model_name or "openai"
            data_atual = datetime.utcnow().strftime("%Y-%m-%d")
            hora_atual = datetime.utcnow().strftime("%H:%M:%S")
            
            try:
                log_tokens_async(
                    projeto=projeto,
                    analysis_type=tipo_tarefa,
                    llm_model=modelo_final,
                    tokens_in=tokens_entrada,
                    tokens_out=tokens_saida,
                    data=data_atual,
                    hora=hora_atual,
                    status_update="completed",
                    job_id=job_id_final
                )
            except Exception as log_error:
                print(f"AVISO: Falha no logging de tokens (não afeta o resultado): {log_error}")

            return {
                'reposta_final': conteudo_resposta,
                'tokens_entrada': tokens_entrada,
                'tokens_saida': tokens_saida,
                'job_id': job_id_final
            }
            
        except Exception as e:
            print(f"ERRO: Falha na chamada à API da OpenAI para o modelo '{modelo_final}'. Causa: {e}")
            raise RuntimeError(f"Erro ao comunicar com a OpenAI: {e}") from e
    
    def executar_prompt_com_rag(
        self,
        tipo_tarefa: str,
        prompt_principal: str,
        instrucoes_extras: str = "",
        usar_rag: bool = False,
        max_token_out: int = 15000,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        return self.executar_prompt(
            tipo_tarefa=tipo_tarefa,
            prompt_principal=prompt_principal,
            instrucoes_extras=instrucoes_extras,
            usar_rag=usar_rag,
            max_token_out=max_token_out,
            job_id=job_id
        )
    
    def executar_prompt_com_modelo(
        self,
        tipo_tarefa: str,
        prompt_principal: str,
        instrucoes_extras: str = "",
        model_name: Optional[str] = None,
        max_token_out: int = 15000,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        return self.executar_prompt(
            tipo_tarefa=tipo_tarefa,
            prompt_principal=prompt_principal,
            instrucoes_extras=instrucoes_extras,
            model_name=model_name,
            max_token_out=max_token_out,
            job_id=job_id
        )