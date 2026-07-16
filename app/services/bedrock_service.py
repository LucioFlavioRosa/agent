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
        max_tokens: int = 40000,
        temperature: float = 0.0,
        company_id: str = "default",
        group_id: Optional[str] = None
    ) -> tuple:
        """Chama o Bedrock via STREAMING e retorna texto e tokens consumidos.

        Usa invoke_model_with_response_stream em vez de invoke_model:
        os chunks chegam continuamente durante a geração, então a conexão
        nunca fica ociosa e o balanceador da Azure (~4 min idle) não a derruba.
        """
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

            # 2. Payload no formato da API do Claude 3 na AWS (igual ao anterior)
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

            # 3. Timeouts: com streaming, o read_timeout vale ENTRE chunks,
            #    não para a geração inteira. 120s entre chunks já é folgado.
            aws_config = Config(
                read_timeout=120,
                connect_timeout=60,
                tcp_keepalive=True,
                retries={'max_attempts': 3, 'mode': 'standard'}
            )

            # 4. CHAMADA ASSÍNCRONA COM STREAMING
            session = aioboto3.Session(
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=aws_region
            )
            async with session.client('bedrock-runtime', config=aws_config) as bedrock_client:
                response = await bedrock_client.invoke_model_with_response_stream(
                    modelId=modelo,
                    contentType='application/json',
                    accept='application/json',
                    body=json.dumps(body)
                )

                partes = []
                input_tokens = 0
                output_tokens = 0

                # Consome o stream de eventos — é isso que mantém a conexão viva
                async for event in response['body']:
                    chunk_bytes = event.get('chunk', {}).get('bytes')
                    if not chunk_bytes:
                        # Eventos de erro do stream (throttling, internal error etc.)
                        for err_key in ('internalServerException', 'modelStreamErrorException',
                                        'throttlingException', 'validationException'):
                            if err_key in event:
                                raise Exception(f"Erro no stream do Bedrock: {event[err_key]}")
                        continue

                    chunk = json.loads(chunk_bytes)
                    tipo = chunk.get('type')

                    if tipo == 'message_start':
                        input_tokens = chunk.get('message', {}).get('usage', {}).get('input_tokens', 0)

                    elif tipo == 'content_block_delta':
                        delta = chunk.get('delta', {})
                        if delta.get('type') == 'text_delta':
                            partes.append(delta.get('text', ''))

                    elif tipo == 'message_delta':
                        output_tokens = chunk.get('usage', {}).get('output_tokens', output_tokens)

                    elif tipo == 'message_stop':
                        # Métricas oficiais do Bedrock no último chunk (mais confiáveis)
                        metrics = chunk.get('amazon-bedrock-invocationMetrics', {})
                        input_tokens = metrics.get('inputTokenCount', input_tokens)
                        output_tokens = metrics.get('outputTokenCount', output_tokens)

                texto_gerado = ''.join(partes)

                print(f"✅ [BEDROCK] Sucesso! Tokens In: {input_tokens} | Out: {output_tokens}", flush=True)
                return texto_gerado, input_tokens, output_tokens

        except Exception as e:
            print(f"❌ [BEDROCK] Erro na chamada para Empresa {company_id}: {str(e)}", flush=True)
            logger.error(f"erro_geracao_bedrock | company_id={company_id} | group_id={group_id} | erro={e}")
            traceback.print_exc()
            raise Exception(f"Falha na IA Bedrock: {str(e)}")
