import os
import uuid
from datetime import datetime
from openai import AzureOpenAI
from typing import Optional, Dict, Any

from domain.interfaces.llm_provider_interface import ILLMProviderComplete
from domain.interfaces.secret_manager_interface import ISecretManager
from services.mongodb_group_resolver_service import MongoDBGroupResolverService
from tools.azure_secret_manager import AzureSecretManager
from utils.constants import VaultType

class OpenAILLMProvider(ILLMProviderComplete):
    def __init__(self, secret_manager: Optional[ISecretManager] = None, user_email: Optional[str] = None, group_resolver: Optional[MongoDBGroupResolverService] = None):
        # Sempre usar VaultType.LLM para buscar secrets de provedores LLM
        self.secret_manager = secret_manager or AzureSecretManager(vault_type=VaultType.LLM)
        self.user_email = user_email
        self.group_resolver = group_resolver or MongoDBGroupResolverService()
        
        try:
            self.azure_endpoint = os.environ["AZURE_OPENAI_MODELS"]
        except KeyError as e:
            raise EnvironmentError(f"ERRO: A variável de ambiente {e} não foi configurada para o Azure OpenAI.")
        
        # Recupera empresa do email
        self.empresa = self._extrair_empresa_do_email(user_email) if user_email else None
        self.grupo = self._resolver_grupo(user_email, self.empresa) if user_email and self.empresa else None
        
        # Recupera API Key do formato correto
        self.api_key = self._recuperar_api_key()
        
        self.openai_client = AzureOpenAI(
            azure_endpoint=self.azure_endpoint,
            api_version="2025-03-01-preview",
            api_key=self.api_key,
        )

    def _extrair_empresa_do_email(self, email: Optional[str]) -> Optional[str]:
        if not email:
            return None
        try:
            # Exemplo: lucio.rosa@peers.com -> peers
            return email.split("@")[-1].split(".")[0]
        except Exception:
            return None

    def _resolver_grupo(self, email: Optional[str], empresa: Optional[str]) -> Optional[str]:
        if not email or not empresa:
            return None
        try:
            grupo = self.group_resolver.resolver_grupo(email, empresa)
            return grupo
        except Exception:
            return None

    def _recuperar_api_key(self) -> str:
        # Nome do secret: openai-token-{grupo}-{empresa}
        if self.grupo and self.empresa:
            secret_name = f"openai-token-{self.grupo}-{self.empresa}"
        else:
            # Fallback para secret padrão
            secret_name = "openai-token"
        try:
            return self.secret_manager.get_secret(secret_name)
        except Exception as e:
            raise EnvironmentError(f"ERRO ao recuperar API Key do Azure Key Vault: {e}")

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
        prompt_sistema = self.carregar_prompt(tipo_tarefa)

        # Concatena instrucoes_extras ao prompt_principal se houver
        if instrucoes_extras and instrucoes_extras.strip():
            prompt_usuario = f"{prompt_principal}\n\nInstruções extras do usuário: {instrucoes_extras.strip()}"
        else:
            prompt_usuario = prompt_principal

        mensagens = [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario}
        ]

        try:
            response = self.openai_client.chat.completions.create(
                model=modelo_final,
                messages=mensagens,
                temperature=0.3,
                max_completion_tokens=max_token_out
            )

            conteudo_resposta = (response.choices[0].message.content or "").strip()
            tokens_entrada = response.usage.prompt_tokens
            tokens_saida = response.usage.completion_tokens
            model_id = modelo_final

            return {
                'reposta_final': conteudo_resposta,
                'tokens_entrada': tokens_entrada,
                'tokens_saida': tokens_saida,
                'job_id': job_id_final,
                'model_id': model_id
            }
        except Exception as e:
            print(f"ERRO: Falha na chamada à API da OpenAI para o modelo '{modelo_final}'. Causa: {e}")
            raise RuntimeError(f"Erro ao comunicar com a OpenAI: {e}") from e
