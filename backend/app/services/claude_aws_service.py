import json
import logging
import sys
from typing import Optional
import aioboto3  # 🚀 Usado para AWS Assíncrono no FastAPI/Starlette
from azure.keyvault.secrets.aio import SecretClient

from backend.app.services.vault_service import VaultService

logger = logging.getLogger("mcp_claude_aws")

class ClaudeAWSService:
    def __init__(self, vault_service: VaultService):
        self.vault_service = vault_service
        self.aws_access_key_id: Optional[str] = None
        self.aws_secret_access_key: Optional[str] = None
        self.aws_region: str = "us-east-1"
        self._is_initialized = False

    async def _initialize_credentials(self):
        """Busca as credenciais no Key Vault apenas uma vez."""
        if self._is_initialized:
            return

        logger.info("[Claude AWS] Buscando credenciais do Amazon Bedrock no Vault...")
        
        for url in self.vault_service.vault_urls:
            try:
                async with SecretClient(vault_url=url, credential=self.vault_service.credential) as secret_client:
                    # NOTA: Ajuste esses nomes se no seu Vault eles estiverem diferentes (ex: AWS-ACCESS-KEY-ID)
                    ak_secret = await secret_client.get_secret("aws-access-key-id")
                    self.aws_access_key_id = ak_secret.value
                    
                    sk_secret = await secret_client.get_secret("aws-secret-access-key")
                    self.aws_secret_access_key = sk_secret.value
                    
                    try:
                        region_secret = await secret_client.get_secret("aws-region")
                        self.aws_region = region_secret.value
                    except Exception:
                        pass # Usa us-east-1 como default

                    logger.info(f"🔑 [Claude AWS] Credenciais da AWS carregadas com sucesso de {url}")
                    self._is_initialized = True
                    break
                    
            except Exception:
                continue 

        if not self._is_initialized:
            logger.error("❌ [Claude AWS] Falha ao carregar credenciais da AWS.")
            raise ValueError("Credenciais AWS ausentes no Key Vault.")

    async def gerar_texto(self, prompt: str, modelo: str) -> str:
        """
        Contrato padrão esperado pelo AgentService.
        Usa aioboto3 para invocar o Bedrock de forma não-bloqueante.
        """
        await self._initialize_credentials()

        # Se o modelo não for enviado pelo mapping, usa o default cross-region do Claude 3.5
        model_id = modelo or "us.anthropic.claude-3-5-sonnet-20241022-v2:0"

        logger.info(f"🧠 [Claude AWS] Iniciando invoke_model no Bedrock... Model: {model_id} | Região: {self.aws_region}")

        # O prompt_sistema (comportamento) já foi mesclado ao 'prompt' gigante no AgentService.
        # Por isso, não precisamos passar "system" separado aqui.
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

        try:
            # 🚀 Criação do cliente Boto3 Assíncrono (aioboto3)
            session = aioboto3.Session(
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.aws_region
            )

            async with session.client('bedrock-runtime') as bedrock_client:
                # O 'await' aqui é a chave! Ele libera o worker para outras tarefas enquanto a AWS pensa.
                response = await bedrock_client.invoke_model(
                    modelId=model_id,
                    contentType='application/json',
                    accept='application/json',
                    body=json.dumps(body)
                )

                # Processa a resposta (Stream assíncrono do corpo)
                response_body_bytes = await response['body'].read()
                response_body = json.loads(response_body_bytes)
                
                content = response_body.get('content', [])
                result = content[0].get('text', '') if content else ""
                
                usage = response_body.get('usage', {})
                logger.info(
                    f"✅ [Claude AWS] Sucesso. Tokens -> In: {usage.get('input_tokens')} | Out: {usage.get('output_tokens')}"
                )
                
                return result

        except Exception as e:
            logger.error(f"❌ [Claude AWS] ERRO CRÍTICO NO BEDROCK: {str(e)}")
            sys.stdout.flush()
            raise RuntimeError(f"Erro ao comunicar com AWS Bedrock: {e}") from e
