import boto3
import json
import uuid
import sys
from typing import Optional, Dict, Any
from domain.interfaces.llm_provider_interface import ILLMProviderComplete
from tools.azure_secret_manager import AzureSecretManager, VaultType
from tools.prompt_utils import carregar_prompt
from tools.user_email_parser import UserEmailParser

class AmazonBedrockProvider(ILLMProviderComplete):
    def __init__(self, secret_manager: Optional[AzureSecretManager] = None, user_email: Optional[str] = None, group_resolver: Optional[object] = None):
        print(f"--- [DEBUG] Iniciando AmazonBedrockProvider para: {user_email} ---", flush=True)
        
        self.secret_manager = secret_manager or AzureSecretManager(vault_type=VaultType.LLM)
        self.user_email = user_email
        self.group_resolver = group_resolver

        if not user_email:
            raise ValueError("user_email é obrigatório para busca de secrets AWS neste projeto.")

        # --- DIAGNÓSTICO DO GRUPO ---
        print(f"[DEBUG] Group Resolver objeto: {group_resolver}", flush=True)
        
        if group_resolver is not None:
            # Obtém grupo diretamente do MongoDB usando o e-mail
            grupo = group_resolver.get_group_for_user(user_email)
            print(f"[DEBUG] Resultado do get_group_for_user: {grupo}", flush=True)
        else:
            print("[DEBUG] AVISO: group_resolver é None! Grupo será definido como None.", flush=True)
            grupo = None
        
        # Obtém usuario e empresa via parser
        usuario, empresa = UserEmailParser.parse_email(user_email)
        print(f"[DEBUG] Parser - Usuario: {usuario}, Empresa: {empresa}", flush=True)

        # Monta os nomes dos secrets AWS conforme padrão
        aws_access_key_secret_name = f"AWS-ACCESS-KEY-ID-{grupo}-{empresa}"
        aws_secret_access_key_secret_name = f"AWS-SECRET-ACCESS-KEY-{grupo}-{empresa}"
        aws_region_secret_name = f"AWS-REGION-{grupo}-{empresa}"

        print(f"[DEBUG] Nome Secret ID montado: '{aws_access_key_secret_name}'", flush=True)
        print(f"[DEBUG] Nome Secret Key montado: '{aws_secret_access_key_secret_name}'", flush=True)

        # Verificação de segurança antes de chamar o cofre
        if grupo is None:
            print("[CRÍTICO] A variável 'grupo' é None. Isso vai causar erro no Key Vault se o secret não tiver 'None' no nome.", flush=True)

        # Tenta buscar os secrets
        print("[DEBUG] Chamando self.secret_manager.get_secret...", flush=True)
        self.aws_access_key_id = self.secret_manager.get_secret(aws_access_key_secret_name)
        self.aws_secret_access_key = self.secret_manager.get_secret(aws_secret_access_key_secret_name)
        self.aws_region = self.secret_manager.get_secret(aws_region_secret_name)
        
        print("[DEBUG] Secrets recuperados com sucesso. Iniciando cliente Boto3...", flush=True)

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
        model_name: Optional[str] = None,
        max_token_out: int = 8000,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        # (O resto do código permanece igual)
        model_id = model_name
        job_id_final = job_id
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
            print(f"Erro no Bedrock: {str(e)}", flush=True)
            raise e
