import boto3
import json
import uuid
import sys # Importado para forçar o flush do print no Azure
from typing import Optional, Dict, Any
from domain.interfaces.llm_provider_interface import ILLMProvider
from services.azure_secret_manager import AzureSecretManager, VaultType
from tools.prompt_utils import carregar_prompt

class AmazonBedrockProvider(ILLMProvider):
    def __init__(self, secret_manager: Optional[AzureSecretManager] = None):
        print("--- INICIANDO CONSTRUTOR BEDROCK ---") # DEBUG
        
        self.secret_manager = secret_manager or AzureSecretManager(vault_type=VaultType.LLM)
        
        # Recuperando segredos
        self.aws_access_key_id = self.secret_manager.get_secret('AWS-ACCESS-KEY-ID')
        self.aws_secret_access_key = self.secret_manager.get_secret('AWS-SECRET-ACCESS-KEY')
        self.aws_region = self.secret_manager.get_secret('AWS-REGION')
        
        # --- BLOCO DE DEBUG (EXECUTA NO STARTUP) ---
        print(f"DEBUG - Região carregada do Vault: '{self.aws_region}'")
        
        # Mascarando chaves para segurança nos logs
        masked_key = f"{self.aws_access_key_id[:4]}...{self.aws_access_key_id[-4:]}" if self.aws_access_key_id else "None"
        print(f"DEBUG - Access Key ID: {masked_key}")
        print(f"DEBUG - Secret Key existe? {'SIM' if self.aws_secret_access_key else 'NAO'}")
        
        sys.stdout.flush() # Garante que apareça no Log Stream do Azure imediatamente
        # -------------------------------------------

        self.bedrock_runtime = boto3.client(
            'bedrock-runtime',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_region
        )
        
        # Confirmação de como o Boto3 foi configurado internamente
        print(f"DEBUG - Boto3 Client configurado para região: {self.bedrock_runtime.meta.region_name}")

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
        
        # 1. Lógica de Model ID
        # ATENÇÃO AQUI: O prefixo 'us.' causa o comportamento cross-region
        default_model = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
        model_id = model_name or default_model
        
        print(f"--- EXECUTANDO PROMPT ---")
        print(f"DEBUG - Model ID solicitado: {model_id}")
        
        job_id_final = job_id or str(uuid.uuid4())
        prompt_sistema = carregar_prompt(tipo_tarefa)
        
        prompt_input = prompt_principal
        if instrucoes_extras.strip():
            prompt_input += f"\n\n--- INSTRUÇÕES EXTRAS ---\n{instrucoes_extras}"
        
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
            "temperature": 0.2,
        }
        
        try:
            print(f"DEBUG - Iniciando invoke_model no Bedrock...")
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
                'resposta_final': result,
                'tokens_entrada': usage.get('input_tokens', 0),
                'tokens_saida': usage.get('output_tokens', 0),
                'job_id': job_id_final,
                'model_id': model_id
            }
        except Exception as e:
            # Log detalhado do erro
            print(f"ERRO CRÍTICO NO BEDROCK: {str(e)}")
            print(f"DEBUG - Região da sessão Boto3 no momento do erro: {self.bedrock_runtime.meta.region_name}")
            sys.stdout.flush()
            raise e
    
    # ... resto do código (executar_prompt_com_modelo) ...
