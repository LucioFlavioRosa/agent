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
        self.key_vault_url = os.environ.get('KEY_VAULT_URL') or getattr(settings, 'KEY_VAULT_URL', None)
        if not self.key_vault_url:
            logger.critical("Variável de ambiente KEY_VAULT_URL não definida.")
            raise EnvironmentError("Variável de ambiente KEY_VAULT_URL não definida.")
        self.secret_manager = AzureSecretManager(self.key_vault_url)

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
                logger.error(f"[KeyVault] Segredo '{secret_name}' NÃO encontrado no Key Vault (404). Tentando fallback para variável de ambiente ou settings.")
            else:
                logger.error(f"Erro ao buscar segredo '{secret_name}' do Key Vault: {e}")
            secret_value = os.environ.get(settings_attr) or getattr(settings, settings_attr, None)
            if secret_value:
                logger.warning(f"Fallback: Segredo '{secret_name}' não encontrado no Key Vault, usando variável de ambiente ou valor default para '{settings_attr}'.")
            else:
                logger.critical(f"Falha crítica: Segredo '{secret_name}' não encontrado no Key Vault nem nas variáveis de ambiente/settings para '{settings_attr}'.")
            return secret_value

    def load_secrets_from_key_vault(self):
        secret_names = self.secret_manager.list_secret_names()
        for secret_name in secret_names:
            secret_value = self._load_single_secret(secret_name)
            settings_attr = kebab_to_upper_snake(secret_name)
            setattr(settings, settings_attr, secret_value)
        logger.info("Todos os segredos sensíveis foram carregados do Key Vault (com fallback para env quando necessário).")
