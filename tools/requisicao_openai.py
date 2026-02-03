import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from openai import AzureOpenAI

# Imports trazidos da referência (Bedrock)
from domain.interfaces.llm_provider_interface import ILLMProviderComplete
from services.azure_secret_manager import AzureSecretManager, VaultType
from tools.user_email_parser import UserEmailParser

class OpenAILLMProvider(ILLMProviderComplete):
    def __init__(self, secret_manager: Optional[AzureSecretManager] = None, user_email: Optional[str] = None, group_resolver: Optional[object] = None):
        self.secret_manager = secret_manager or AzureSecretManager(vault_type=VaultType.LLM)
        self.user_email = user_email
        self.group_resolver = group_resolver

        # 2. Validação de e-mail obrigatória
        if not user_email:
            raise ValueError("user_email é obrigatório para busca de secrets Azure OpenAI neste projeto.")

        # 3. Lógica de Parse solicitada
        grupo, empresa = UserEmailParser.parse_email_with_group(user_email, group_resolver=self.group_resolver)

        try:
            # 4. Leitura dos segredos usando get_secret_with_user_context
            # Substituímos as variáveis de ambiente pela busca no Vault com contexto
            # Nota: Ajuste os nomes das chaves ('AZURE-OPENAI-KEY', etc) conforme estão no seu Vault
            
            api_key = self.secret_manager.get_secret_with_user_context(
                'AZURE-OPENAI-KEY', 
                user_email, 
                group_resolver=self.group_resolver
            )
            
            self.azure_endpoint = self.secret_manager.get_secret_with_user_context(
                'AZURE-OPENAI-ENDPOINT', 
                user_email, 
                group_resolver=self.group_resolver
            )

            self.openai_client = AzureOpenAI(
                azure_endpoint=self.azure_endpoint,
                api_version="2025-03-01-preview",
                api_key=api_key,
            )

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
        model_name: Optional[str] = None,
        max_token_out: int = 15000,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        modelo_final = model_name or os.environ.get("AZURE_DEFAULT_DEPLOYMENT_NAME")
        job_id_final = job_id or str(uuid.uuid4())
        
        prompt_sistema_base = self.carregar_prompt(tipo_tarefa)
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
            
            return {
                'reposta_final': conteudo_resposta,
                'tokens_entrada': tokens_entrada,
                'tokens_saida': tokens_saida,
                'job_id': job_id_final
            }
            
        except Exception as e:
            nome_modelo_erro = modelo_final or "modelo não especificado"
            print(f"ERRO: Falha na chamada à API da OpenAI para o modelo '{nome_modelo_erro}'. C
