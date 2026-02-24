import json
import logging
import sys
from typing import Optional
import aioboto3
from azure.keyvault.secrets.aio import SecretClient

from backend.app.services.vault_service import VaultService

logger = logging.getLogger("mcp_claude_aws")

class ClaudeAWSService:
    def __init__(self, vault_service: VaultService):
        self.vault_service = vault_service
        # Não guardamos mais as credenciais na classe (self) para não misturar clientes!

    async def gerar_texto(self, prompt: str, modelo: str, company_id: str, group_id: Optional[str] = None) -> str:
        """
        Gera texto usando AWS Bedrock, buscando as credenciais dinamicamente 
        para a empresa (company_id) que solicitou a análise.
        """
        logger.info(f"[Claude AWS] Buscando credenciais para company_id='{company_id}'")
        
        # 1. Busca as credenciais usando o padrão do seu VaultService (company/group)
        # O vault_service já cuida do fallback (com ou sem group_id) e do cache!
        aws_access_key_id = await self.vault_service.get_secret("aws-access-key-id", company_id, group_id)
        aws_secret_access_key = await self.vault_service.get_secret("aws-secret-access-key", company_id, group_id)
        
        if not aws_access_key_id or not aws_secret_access_key:
            logger.error(f"❌ [Claude AWS] Credenciais ausentes para company_id='{company_id}'")
            raise ValueError(f"Credenciais AWS ausentes no Key Vault para a empresa {company_id}.")

        # Tenta buscar a região, se não existir usa o fallback padrão
        aws_region = await self.vault_service.get_secret("aws-region", company_id, group_id)
        if not aws_region:
            aws_region = "us-east-1"

        # 2. Prepara o payload do modelo
        model_id = modelo or "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
        logger.info(f"🧠 [Claude AWS] Iniciando invoke_model no Bedrock... Model: {model_id} | Região: {aws_region}")

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}]
                }
            ],
            "max_tokens": 8000,
            "temperature": 0.2,
        }

        # 3. Invoca o Bedrock de forma isolada e segura para este request
        try:
            session = aioboto3.Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=aws_region
            )

            async with session.client('bedrock-runtime') as bedrock_client:
                response = await bedrock_client.invoke_model(
                    modelId=model_id,
                    contentType='application/json',
                    accept='application/json',
                    body=json.dumps(body)
                )

                response_body_bytes = await response['body'].read()
                response_body = json.loads(response_body_bytes)
                
                content = response_body.get('content', [])
                result = content[0].get('text', '') if content else ""
                
                usage = response_body.get('usage', {})
                logger.info(
                    f"✅ [Claude AWS] Sucesso. Tokens -> In: {usage.get('input_tokens', 0)} | Out: {usage.get('output_tokens', 0)}"
                )
                
                return result

        except Exception as e:
            logger.error(f"❌ [Claude AWS] ERRO CRÍTICO NO BEDROCK: {str(e)}")
            sys.stdout.flush()
            raise RuntimeError(f"Erro ao comunicar com AWS Bedrock: {e}") from e
