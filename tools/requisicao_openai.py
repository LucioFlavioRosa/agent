import os
import uuid
from datetime import datetime
from openai import AzureOpenAI
from typing import Optional, Dict, Any
from domain.interfaces.llm_provider_interface import ILLMProviderComplete
from services.azure_secret_manager import AzureSecretManager, VaultType
from tools.prompt_utils import carregar_prompt

class OpenAILLMProvider(ILLMProviderComplete):
    def __init__(self):
        
        self.secret_manager = AzureSecretManager(vault_type=VaultType.LLM)
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
        prompt_sistema_base = carregar_prompt(tipo_tarefa)
        prompt_sistema_final = prompt_sistema_base
        
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
            return {
                'reposta_final': conteudo_resposta,
                'tokens_entrada': tokens_entrada,
                'tokens_saida': tokens_saida,
                'job_id': job_id_final
            }
        except Exception as e:
            print(f"ERRO: Falha na chamada à API da OpenAI para o modelo '{modelo_final}'. Causa: {e}")
            raise RuntimeError(f"Erro ao comunicar com a OpenAI: {e}") from e
        
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
