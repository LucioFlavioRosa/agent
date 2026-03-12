import json
import logging
import traceback
import aioboto3 
from typing import Optional
from botocore.config import Config

logger = logging.getLogger("mcp_prototype.bedrock_service")

class LLMService:
    def __init__(self, vault_service):
        """
        Inicializa o serviço. 
        Nota: Não criamos a sessão aioboto3 aqui no __init__ porque as credenciais
        podem variar por empresa/grupo.
        """
        self.vault_service = vault_service

    async def gerar_texto(
        self, 
        prompt: str, 
        modelo: str = "anthropic.claude-3-5-sonnet-20240620-v1:0",
        max_tokens: int = 30000,
        temperature: float = 0.0,
        company_id: str = "default",
        group_id: Optional[str] = None
    ) -> tuple: # 🚀 AGORA RETORNA UMA TUPLA (texto, in_tokens, out_tokens)
        """Chama o Bedrock de forma ASSÍNCRONA e retorna texto e tokens consumidos"""

        try:
            print(f"📡 [BEDROCK] Iniciando geração para Empresa {company_id} e Grupo {group_id}...", flush=True)

            # 1. Busca credenciais no Vault
            aws_access_key = await self.vault_service.get_secret(
                "aws-access-key-id", 
                company_id=company_id, 
                group_id=group_id,
                vault_type="llm"
            )
            aws_secret_key = await self.vault_service.get_secret(
                "aws-secret-access-key", 
                company_id=company_id, 
                group_id=group_id, 
                vault_type="llm"
            )
            aws_region = await self.vault_service.get_secret(
                "aws-region", 
                company_id=company_id,
                group_id=group_id, 
                vault_type="llm"
            )

            if not all([aws_access_key, aws_secret_key, aws_region]):
                raise ValueError(f"Credenciais AWS incompletas no cofre para a empresa {company_id} (Grupo: {group_id})")

            # 2. Prepara o payload no formato exigido pela API do Claude 3 na AWS
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": prompt}]
                    }
                ]
            }

            # 3. Configurações de timeout
            aws_config = Config(
                read_timeout=300,  
                connect_timeout=60,
                retries={'max_attempts': 3, 'mode': 'standard'}
            )

            # 4. CHAMADA ASSÍNCRONA
            session = aioboto3.Session(
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=aws_region
            )

            async with session.client('bedrock-runtime', config=aws_config) as bedrock_client:
                response = await bedrock_client.invoke_model(
                    modelId=modelo,
                    contentType='application/json',
                    accept='application/json',
                    body=json.dumps(body)
                )

                response_body_bytes = await response['body'].read()
                response_body = json.loads(response_body_bytes)
                
                # 🚀 EXTRAÇÃO DOS TOKENS
                texto_gerado = response_body.get('content', [{}])[0].get('text', '')
                usage = response_body.get('usage', {})
                input_tokens = usage.get('input_tokens', 0)
                output_tokens = usage.get('output_tokens', 0)
                
                print(f"✅ [BEDROCK] Sucesso! Tokens In: {input_tokens} | Out: {output_tokens}", flush=True)
                
                # 🚀 DEVOLVE O TEXTO E AS MÉTRICAS
                return texto_gerado, input_tokens, output_tokens

        except Exception as e:
            print(f"❌ [BEDROCK] Erro na chamada para Empresa {company_id}: {str(e)}", flush=True)
            logger.error(f"erro_geracao_bedrock | company_id={company_id} | group_id={group_id} | erro={e}")
            traceback.print_exc()
            raise Exception(f"Falha na IA Bedrock: {str(e)}")
