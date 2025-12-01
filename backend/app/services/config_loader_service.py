import os
import logging
from backend.app.core.config import settings
from backend.app.services.azure_secret_manager import AzureSecretManager

class ConfigLoaderService:
    """
    Serviço responsável por carregar segredos sensíveis dos Key Vaults Azure e popular dinamicamente o objeto settings.
    Implementa cache em memória para evitar múltiplas leituras e fallback para variáveis de ambiente.
    """
    _secret_cache = {}
    _vault_map = {
        'azure': 'kv-codeai-azure-dev-usc',
        'devops': 'kv-codeai-devops-dev-usc',
        'github': 'kv-codeai-github-dev-usc',
        'llm': 'kv-codeai-llm-dev-usc'
    }
    _secrets_by_vault = {
        'azure': [
            'AZURE_AD_CLIENT_SECRET',
            'AZURE_STORAGE_CONNECTION_STRING',
            'JWT_SECRET_KEY'
        ],
        'devops': [],
        'github': [],
        'llm': []
    }

    def _get_secret_manager(self, vault_key):
        # Não define mais os.environ['KEY_VAULT_URL'] dinamicamente
        # O AzureSecretManager recebe o vault_type e resolve a URL via variáveis de ambiente internamente
        return AzureSecretManager(vault_type=vault_key)

    def load_secrets_from_key_vault(self):
        logger = logging.getLogger("ConfigLoaderService")
        for vault_key, secrets in self._secrets_by_vault.items():
            if not secrets:
                continue
            try:
                secret_manager = self._get_secret_manager(vault_key)
                for secret_name in secrets:
                    cache_key = f"{vault_key}:{secret_name}"
                    if cache_key in self._secret_cache:
                        secret_value = self._secret_cache[cache_key]
                    else:
                        try:
                            secret_value = secret_manager.get_secret(secret_name)
                            self._secret_cache[cache_key] = secret_value
                        except Exception as e:
                            logger.error(f"Erro ao buscar segredo '{secret_name}' do Key Vault '{vault_key}': {e}")
                            secret_value = os.environ.get(secret_name) or getattr(settings, secret_name, None)
                            if not secret_value:
                                logger.warning(f"Fallback: Segredo '{secret_name}' não encontrado no Key Vault nem nas variáveis de ambiente.")
                    # Atualiza dinamicamente o objeto settings
                    setattr(settings, secret_name, secret_value)
                    logger.info(f"Segredo '{secret_name}' carregado para settings via Key Vault '{vault_key}'.")
            except Exception as e:
                logger.error(f"Falha ao inicializar SecretManager para Key Vault '{vault_key}': {e}")
        logger.info("Todos os segredos sensíveis foram carregados do Key Vault (com fallback para env quando necessário).")
