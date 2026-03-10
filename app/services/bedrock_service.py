import json
import logging
import boto3
import traceback
from typing import Optional
from botocore.config import Config

logger = logging.getLogger("mcp_prototype.bedrock_service")

class LLMService:
    def __init__(self, vault_service):
        """
        Inicializa o serviço. 
        Nota: Não criamos o cliente boto3 aqui no __init__ porque as credenciais
        podem variar por empresa/grupo.
        """
        self.vault_service = vault_service

    async def _get_bedrock_client(self, company_id: str, group_id: Optional[str] = None):
        """Busca credenciais no Vault e cria o cliente AWS"""
        try:
            # 🚀 LÓGICA DE BUSCA: Passamos group_id. 
            # O VaultService tentará: base-company-group -> base-company

            aws_access_key = await self.vault_service.get_secret(
                "aws-access-key-id", 
                company_id=company_id, 
                group_id=group_id, # 🎯 Mudamos para group_id conforme solicitado
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

            return boto3.client(
                service_name='bedrock-runtime',
                region_name=aws_region,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                config=Config(retries={'max_attempts': 3, 'mode': 'standard'})
            )
        except Exception as e:
            logger.error(f"erro_criacao_cliente_bedrock | company_id={company_id} | group_id={group_id} | erro={e}")
            raise

    async def gerar_texto(
        self, 
        prompt: str, 
        modelo: str = "anthropic.claude-3-5-sonnet-20240620-v1:0",
        max_tokens: int = 4096,
        temperature: float = 0.0,
        company_id: str = "default",
        group_id: Optional[str] = None # 🚀 Recebe group_id vindo do queue_service
    ) -> str:
        """Chama o Bedrock para gerar o código HTML"""

        try:
            print(f"📡 [BEDROCK] Iniciando geração para Empresa {company_id} e Grupo {group_id}...", flush=True)

            # Obtém o cliente AWS configurado para este contexto específico
            client = await self._get_bedrock_client(company_id, group_id)

            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": prompt}]
                    }
                ]
            })

            # Execução síncrona dentro da thread do worker
            response = client.invoke_model(
                modelId=modelo,
                body=body
            )

            response_body = json.loads(response.get('body').read())
            texto_gerado = response_body.get('content', [{}])[0].get('text', '')
            
            return texto_gerado

        except Exception as e:
            print(f"❌ [BEDROCK] Erro na chamada para Empresa {company_id}: {str(e)}", flush=True)
            traceback.print_exc()
            raise Exception(f"Falha na IA Bedrock: {str(e)}")
