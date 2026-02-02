import boto3
import json
import uuid
from typing import Optional, Dict, Any
from domain.interfaces.llm_provider_interface import ILLMProviderComplete
from services.azure_secret_manager import AzureSecretManager, VaultType
from tools.prompt_utils import carregar_prompt

class AmazonBedrockProvider(ILLMProviderComplete):
    def __init__(self, rag_retriever: Optional[Any] = None, secret_manager: Optional[AzureSecretManager] = None):
        self.rag_retriever = rag_retriever
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
        max_token_out: int = 8000,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        default_model = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
        model_id = model_name or default_model
        job_id_final = job_id or str(uuid.uuid4())
        prompt_sistema = carregar_prompt(tipo_tarefa)
        prompt_input = prompt_principal
        if instrucoes_extras.strip():
            prompt_input += f"\n--- INSTRUÇÕES EXTRAS ---\n{instrucoes_extras}"
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt_input}]
                }
            ],
            "system": prompt_sistema,
            "max_tokens": max_token_out,
            "temperature": 0.2
        }
        try:
            response = self.bedrock_runtime.invoke_model(
                modelId=model_id,
                contentType='application/json',
                accept='application/json',
                body=json.dumps(body)
            )
            response_body = json.loads(response['body'].read())
            content = response_body.get('content', [])
            result = content[0].get('text', '') if content else ""
            usage = response_body.get('usage', {})
            return {
                'reposta_final': result,
                'tokens_entrada': usage.get('input_tokens', 0),
                'tokens_saida': usage.get('output_tokens', 0),
                'job_id': job_id_final,
                'model_id': model_id
            }
        except Exception as e:
            print(f"Erro no Bedrock: {str(e)}")
            raise e

    def executar_prompt_com_modelo(
        self,
        tipo_tarefa: str,
        prompt_principal: str,
        instrucoes_extras: str = "",
        model_name: Optional[str] = None,
        max_token_out: int = 8000,
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
