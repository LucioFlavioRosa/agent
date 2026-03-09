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
        podem variar por empresa/projeto.
        """
        self.vault_service = vault_service

    async def _get_bedrock_client(self, company_id: str, job_id: Optional[str] = None):
        """Busca credenciais no Vault e cria o cliente AWS"""
        try:
            # 🚀 BUSCA DINÂMICA: Segue a regra base-company-job -> base-company
            # Passamos o job_id para o VaultService localizar os segredos específicos se existirem
            
            aws_access_key = await self.vault_service.get_secret(
                "aws-access-key-id", 
                company_id=company_id, 
                job_id=job_id, 
                vault_type="llm"
            )
            aws_secret_key = await self.vault_service.get_secret(
                "aws-secret-access-key", 
                company_id=company_id, 
                job_id=job_id, 
                vault_type="llm"
            )
            aws_region = await self.vault_service.get_secret(
                "aws-region", 
                company_id=company_id, 
                job_id=job_id, 
                vault_type="llm"
            )

            if not all([aws_access_key, aws_secret_key, aws_region]):
                raise ValueError(f"Credenciais AWS incompletas no cofre para a empresa {company_id} (Job: {job_id})")

            return boto3.client(
                service_name='bedrock-runtime',
                region_name=aws_region,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                config=Config(retries={'max_attempts': 3, 'mode': 'standard'})
            )
        except Exception as e:
            logger.error(f"erro_criacao_cliente_bedrock | company_id={company_id} | job_id={job_id} | erro={e}")
            raise

    async def gerar_texto(
        self, 
        prompt: str, 
        modelo: str = "anthropic.claude-3-5-sonnet-20240620-v1:0",
        max_tokens: int = 4096,
        temperature: float = 0.0,
        company_id: str = "default",
        job_id: Optional[str] = None # 🚀 Adicionado suporte ao job_id
    ) -> str:
        """Chama o Bedrock para gerar o código HTML"""
        
        try:
            print(f"📡 [BEDROCK] Iniciando geração para empresa {company_id} e Job {job_id}...", flush=True)
            
            # Obtém o cliente com as credenciais resolvidas pelo Vault
            client = await self._get_bedrock_client(company_id, job_id)
            
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

            response = client.invoke_model(
                modelId=modelo,
                body=body
            )

            response_body = json.loads(response.get('body').read())
            texto_gerado = response_body.get('content', [{}])[0].get('text', '')
            
            return texto_gerado

        except Exception as e:
            print(f"❌ [BEDROCK] Erro na chamada para Job {job_id}: {str(e)}", flush=True)
            traceback.print_exc()
            raise Exception(f"Falha na IA Bedrock: {str(e)}")
