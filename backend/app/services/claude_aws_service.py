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
        logger.info(f"[ClaudeAWSService] gerar_texto chamado: company_id='{company_id}', group_id='{group_id}', modelo='{modelo}'")
        
        # 1. Busca as credenciais usando o padrão do seu VaultService (company/group)
        # O vault_service já cuida do fallback (com ou sem group_id) e do cache!
        logger.info(f"[ClaudeAWSService] Buscando AWS access key para company_id='{company_id}', group_id='{group_id}'")
        aws_access_key_id = await self.vault_service.get_secret("aws-access-key-id", company_id, group_id)
        logger.info(f"[ClaudeAWSService] Buscando AWS secret key para company_id='{company_id}', group_id='{group_id}'")
        aws_secret_access_key = await self.vault_service.get_secret("aws-secret-access-key", company_id, group_id)
        
        if not aws_access_key_id or not aws_secret_access_key:
            logger.error(f"❌ [ClaudeAWSService] Credenciais ausentes para company_id='{company_id}'")
            raise ValueError(f"Credenciais AWS ausentes no Key Vault para a empresa {company_id}.")

        logger.info(f"[ClaudeAWSService] Buscando AWS region para company_id='{company_id}', group_id='{group_id}'")
        aws_region = await self.vault_service.get_secret("aws-region", company_id, group_id)
        if not aws_region:
            aws_region = "us-east-1"
            logger.info(f"[ClaudeAWSService] Região não encontrada, usando fallback padrão: '{aws_region}'")

        # 2. Prepara o payload do modelo
        model_id = modelo or "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
        logger.info(f"[ClaudeAWSService] Preparando payload para Bedrock. Model: {model_id} | Região: {aws_region}")

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
            logger.info(f"[ClaudeAWSService] Criando sessão boto3 para Bedrock.")
            session = aioboto3.Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=aws_region
            )

            logger.info(f"[ClaudeAWSService] Invocando Bedrock para gerar texto.")
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
                    f"✅ [ClaudeAWSService] Sucesso. Tokens -> In: {usage.get('input_tokens', 0)} | Out: {usage.get('output_tokens', 0)}"
                )
                logger.info(f"[ClaudeAWSService] Texto gerado com sucesso para company_id='{company_id}'")
                
                return result

        except Exception as e:
            logger.error(f"❌ [ClaudeAWSService] ERRO CRÍTICO NO BEDROCK: {str(e)}", exc_info=True)
            sys.stdout.flush()
            raise RuntimeError(f"Erro ao comunicar com AWS Bedrock: {e}") from e
