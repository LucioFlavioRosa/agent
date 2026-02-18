import os
import logging
from backend.app.core.config import settings
from backend.app.services.azure_secret_manager import AzureSecretManager

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("ConfigLoaderService")

def kebab_to_upper_snake(name: str) -> str:
    return name.replace('-', '_').upper()

class ConfigLoaderService:
    _secret_cache = {}

    def __init__(self):
        self.key_vault_url = os.environ.get('KEY_VAULT_URL')
        if not self.key_vault_url:
            logger.critical("Variável de ambiente KEY_VAULT_URL não definida.")
            # Para evitar crash imediato se rodar local sem KV, pode-se tratar aqui,
            # mas mantendo sua lógica original de raise:
            raise EnvironmentError("Variável de ambiente KEY_VAULT_URL não definida.")
        self.secret_manager = AzureSecretManager(self.key_vault_url)

    def _get_secret_with_fallback(self, secret_name: str) -> str:
        settings_attr = kebab_to_upper_snake(secret_name)
        # Tenta pegar da variável de ambiente ou do valor padrão do settings
        secret_value = os.environ.get(settings_attr) or getattr(settings, settings_attr, None)
        
        if secret_value:
            logger.warning(f"Fallback: Segredo '{secret_name}' não encontrado no Key Vault, usando variável de ambiente ou valor default para '{settings_attr}'.")
        else:
            # Loga erro mas retorna None para não quebrar o loop principal imediatamente, 
            # a menos que seja crítico para o startup do serviço específico depois.
            logger.critical(f"Falha crítica: Segredo '{secret_name}' não encontrado no Key Vault nem nas variáveis de ambiente/settings para '{settings_attr}'.")
        return secret_value

    def _load_single_secret(self, secret_name: str) -> str:
        cache_key = secret_name
        settings_attr = kebab_to_upper_snake(secret_name)
        
        if cache_key in self._secret_cache:
            secret_value = self._secret_cache[cache_key]
            logger.info(f"Segredo '{secret_name}' recuperado do cache.")
            return secret_value
        
        try:
            secret_value = self.secret_manager.get_secret(secret_name)
            self._secret_cache[cache_key] = secret_value
            logger.info(f"Segredo '{secret_name}' carregado com sucesso do Key Vault.")
            return secret_value
        except Exception as e:
            error_msg = str(e)
            if '404' in error_msg or 'not found' in error_msg.lower():
                logger.error(f"[KeyVault] Segredo '{secret_name}' NÃO encontrado no Key Vault (404). Tentando fallback.")
            else:
                logger.error(f"Erro ao buscar segredo '{secret_name}' do Key Vault: {e}")
            
            return self._get_secret_with_fallback(secret_name)

    def load_secrets_from_key_vault(self):
        """
        Carrega segredos, mas FILTRA apenas os que existem na classe Settings.
        Isso evita o erro 'Settings object has no field'.
        """
        try:
            # 1. Lista todos os segredos disponíveis no cofre
            secret_names = self.secret_manager.list_secret_names()
            
            for secret_name in secret_names:
                settings_attr = kebab_to_upper_snake(secret_name)

                # 2. VERIFICAÇÃO DE SEGURANÇA (A CORREÇÃO):
                # Só tentamos carregar se o campo existir na classe Settings
                if hasattr(settings, settings_attr):
                    secret_value = self._load_single_secret(secret_name)
                    
                    # Só faz o set se tivermos algum valor (seja do KV ou do fallback)
                    if secret_value is not None:
                        setattr(settings, settings_attr, secret_value)
                else:
                    # Se não existe no Settings (ex: azure-storage), ignoramos silenciosamente ou com aviso
                    logger.warning(f"Segredo '{secret_name}' ignorado (campo '{settings_attr}' não existe em Settings).")

            logger.info("Carga de segredos finalizada.")
            
        except Exception as e:
            logger.error(f"Erro crítico durante a iteração de segredos: {str(e)}")
            raise
