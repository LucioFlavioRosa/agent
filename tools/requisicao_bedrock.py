import boto3
import uuid
from typing import Optional, Dict, Any
from domain.interfaces.llm_provider_interface import ILLMProvider
from services.azure_secret_manager import AzureSecretManager, VaultType
from tools.prompt_utils import carregar_prompt

class AmazonBedrockProvider(ILLMProvider):
    def __init__(self, secret_manager: Optional[AzureSecretManager] = None):
        self.secret_manager = secret_manager or AzureSecretManager(vault_type=VaultType.LLM)
        self.aws_access_key_id = self.secret_manager.get_secret('AWS-ACCESS-KEY-ID')
        self.aws_secret_access_key = self.secret_manager.get_secret('AWS-SECRET-ACCESS-KEY')
        self.aws_region = self.secret_manager.get_secret('AWS-REGION')
        self.bedrock_runtime = boto3.client(
            'bedrock-runtime',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_region
        )

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
        model_id = model_name or "anthropic.claude-3-sonnet-20240229-v1:0"
        job_id_final = job_id or str(uuid.uuid4())
        prompt_sistema = carregar_prompt(tipo_tarefa)
        prompt_input = prompt_principal
        if instrucoes_extras.strip():
            prompt_input += f"\n\n--- INSTRUÇÕES EXTRAS ---\n{instrucoes_extras}"
        body = {
            "prompt": prompt_input,
            "max_tokens": max_token_out,
            "temperature": 0.3
        }
        try:
            response = self.bedrock_runtime.invoke_model(
                modelId=model_id,
                body=str(body).encode('utf-8')
            )
            result = response['body'].read().decode('utf-8')
            tokens_entrada = response.get('usage', {}).get('input_tokens', None)
            tokens_saida = response.get('usage', {}).get('output_tokens', None)
            return {
                'reposta_final': result,
                'tokens_entrada': tokens_entrada,
                'tokens_saida': tokens_saida
            }
        except Exception as e:
            raise RuntimeError(f"Erro ao comunicar com Amazon Bedrock: {e}")

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
