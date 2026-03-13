import json
import logging
import sys
from typing import Optional, Tuple
import aioboto3
from botocore.config import Config
from azure.keyvault.secrets.aio import SecretClient

from backend.app.services.vault_service import VaultService

logger = logging.getLogger("mcp_claude_aws")
logger.setLevel(logging.INFO)

class ClaudeAWSService:
    def __init__(self, vault_service: VaultService):
        self.vault_service = vault_service

    # 🚀 AGORA RETORNA UMA TUPLA COM OS TOKENS 🚀
    async def gerar_texto(self, prompt: str, modelo: str, company_id: str, group_id: Optional[str] = None) -> Tuple[str, int, int]:
        print(f"🚀 [TESTE DEBUG] Chegou na função da AWS! Empresa: {company_id}", flush=True)
        logger.info(f"llm_invocacao_iniciada | company_id={company_id} | group_id={group_id} | modelo={modelo}")
        
        aws_access_key_id = await self.vault_service.get_secret("aws-access-key-id", company_id, group_id)
        aws_secret_access_key = await self.vault_service.get_secret("aws-secret-access-key", company_id, group_id)
        
        if not aws_access_key_id or not aws_secret_access_key:
            logger.error(f"llm_invocacao_erro | company_id={company_id} | motivo=credenciais_ausentes")
            raise ValueError(f"Credenciais AWS ausentes no Key Vault para a empresa {company_id}.")
            
        aws_region = await self.vault_service.get_secret("aws-region", company_id, group_id)
        if not aws_region:
            aws_region = "us-east-1"
            
        model_id = modelo or "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
        
        tamanho_texto = len(str(prompt))
        estimativa_tokens_entrada = tamanho_texto // 4
        
        print(f"📊 [TOKENS] Tamanho do texto: {tamanho_texto} caracteres | Estimativa de Entrada: ~{estimativa_tokens_entrada} tokens", flush=True)
        print(f"⏳ [AWS BEDROCK] Iniciando processamento no Claude. Aguardando... (Pode levar de 2 a 5 minutos)", flush=True)

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}]
                }
            ],
            "max_tokens": 15000,
            "temperature": 0.2,
        }
        
        aws_config = Config(
            read_timeout=300, 
            connect_timeout=60,
            retries={'max_attempts': 1}
        )

        try:
            session = aioboto3.Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=aws_region
            )
            
            async with session.client('bedrock-runtime', config=aws_config) as bedrock_client:
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
                
                # 🚀 EXTRAÇÃO DOS TOKENS REAIS COBRADOS PELA AWS 🚀
                usage = response_body.get('usage', {})
                input_tokens = usage.get('input_tokens', 0)
                output_tokens = usage.get('output_tokens', 0)
                
                print(f"✅ [AWS SUCESSO] O Claude terminou o relatório! Tokens Faturados -> Entrada: {input_tokens} | Saída: {output_tokens}", flush=True)
                
                # RETORNA A TUPLA DE TRÊS ITENS
                return result, input_tokens, output_tokens
                
        except Exception as e:
            print(f"❌ [AWS ERRO FATAL] Falha na comunicação com o Bedrock: {e}", flush=True)
            logger.error(f"llm_invocacao_erro | company_id={company_id} | modelo={model_id} | region={aws_region} | erro={str(e)}")
            sys.stdout.flush()
            raise RuntimeError(f"Erro ao comunicar com AWS Bedrock: {e}") from e
