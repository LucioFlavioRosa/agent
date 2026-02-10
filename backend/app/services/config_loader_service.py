import os
import logging
from backend.app.core.config import settings
from backend.app.services.azure_secret_manager import AzureSecretManager

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("ConfigLoaderService")

class ConfigLoaderService:
    _secret_cache = {}
    _vault_map = {
        'azure': 'kv-codeai-azure-dev-usc'
    }
    _secrets_by_vault = {
        'azure': [
            'redis-host',
            'redis-port',
            'redis-password',
            'redis-db',
            'redis-use-ssl',
            'redis-ssl-cert-reqs'
        ]
    }
    _secret_name_to_settings_attr = {
        'redis-host': 'REDIS_HOST',
        'redis-port': 'REDIS_PORT',
        'redis-password': 'REDIS_PASSWORD',
        'redis-db': 'REDIS_DB',
        'redis-use-ssl': 'REDIS_USE_SSL',
        'redis-ssl-cert-reqs': 'REDIS_SSL_CERT_REQS'
    }

    def _get_secret_manager(self, vault_key):
        return AzureSecretManager(vault_type=vault_key)

    def _load_single_secret(self, vault_key: str, secret_name: str) -> str:
        cache_key = f"{vault_key}:{secret_name}"
        settings_attr = self._secret_name_to_settings_attr.get(secret_name, secret_name.upper().replace('-', '_'))
        if cache_key in self._secret_cache:
            secret_value = self._secret_cache[cache_key]
            logger.info(f"Segredo '{secret_name}' recuperado do cache para Key Vault '{vault_key}'.")
            return secret_value
        try:
            secret_manager = self._get_secret_manager(vault_key)
            secret_value = secret_manager.get_secret(secret_name)
            self._secret_cache[cache_key] = secret_value
            logger.info(f"Segredo '{secret_name}' carregado com sucesso do Key Vault '{vault_key}'.")
            return secret_value
        except Exception as e:
            error_msg = str(e)
            if '404' in error_msg or 'not found' in error_msg.lower():
                logger.error(f"[KeyVault] Segredo '{secret_name}' NÃO encontrado no Key Vault '{vault_key}' (404). Tentando fallback para variável de ambiente ou settings.")
            else:
                logger.error(f"Erro ao buscar segredo '{secret_name}' do Key Vault '{vault_key}': {e}")
            secret_value = os.environ.get(settings_attr) or getattr(settings, settings_attr, None)
            if secret_value:
                logger.warning(f"Fallback: Segredo '{secret_name}' não encontrado no Key Vault '{vault_key}', usando variável de ambiente ou valor default para '{settings_attr}'.")
            else:
                logger.critical(f"Falha crítica: Segredo '{secret_name}' não encontrado no Key Vault '{vault_key}' nem nas variáveis de ambiente/settings para '{settings_attr}'.")
            return secret_value

    def load_secrets_from_key_vault(self):
        for vault_key, secrets in self._secrets_by_vault.items():
            if not secrets:
                continue
            for secret_name in secrets:
                secret_value = self._load_single_secret(vault_key, secret_name)
                settings_attr = self._secret_name_to_settings_attr.get(secret_name, secret_name.upper().replace('-', '_'))
                setattr(settings, settings_attr, secret_value)
        logger.info("Todos os segredos sensíveis foram carregados do Key Vault (com fallback para env quando necessário).")
