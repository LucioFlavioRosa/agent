import os
import logging
from backend.app.core.config import settings
from backend.app.services.azure_secret_manager import AzureSecretManager

# Configuração global de logging para o módulo
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("ConfigLoaderService")

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
    # Passo 1: Corrigir nomes dos segredos para hífens
    _secrets_by_vault = {
        'azure': [
            'azure-ad-client-secret',
            'azure-storage-connection-string',
            'azure-storage-container-name',
            'jwt-secret-key'
        ],
        'devops': [],
        'github': [],
        'llm': []
    }
    # Passo 2: Mapeamento de nomes do Key Vault (hífens) para settings (underscores)
    _secret_name_to_settings_attr = {
        'azure-ad-client-secret': 'AZURE_AD_CLIENT_SECRET',
        'azure-storage-connection-string': 'AZURE_STORAGE_CONNECTION_STRING',
        'azure-storage-container-name': 'AZURE_STORAGE_CONTAINER_NAME',
        'jwt-secret-key': 'JWT_SECRET_KEY'
    }

    def _get_secret_manager(self, vault_key):
        # Não define mais os.environ['KEY_VAULT_URL'] dinamicamente
        # O AzureSecretManager recebe o vault_type e resolve a URL via variáveis de ambiente internamente
        return AzureSecretManager(vault_type=vault_key)

    def load_secrets_from_key_vault(self):
        for vault_key, secrets in self._secrets_by_vault.items():
            if not secrets:
                continue
            try:
                secret_manager = self._get_secret_manager(vault_key)
                for secret_name in secrets:
                    cache_key = f"{vault_key}:{secret_name}"
                    settings_attr = self._secret_name_to_settings_attr.get(secret_name, secret_name.upper().replace('-', '_'))
                    secret_value = None
                    if cache_key in self._secret_cache:
                        secret_value = self._secret_cache[cache_key]
                        logger.info(f"Segredo '{secret_name}' recuperado do cache para Key Vault '{vault_key}'.")
                    else:
                        try:
                            secret_value = secret_manager.get_secret(secret_name)
                            self._secret_cache[cache_key] = secret_value
                            logger.info(f"Segredo '{secret_name}' carregado com sucesso do Key Vault '{vault_key}'.")
                        except Exception as e:
                            # Passo 5: Tratamento de erro robusto
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
                    # Passo 2: Atualiza dinamicamente o objeto settings usando o mapeamento
                    setattr(settings, settings_attr, secret_value)
            except Exception as e:
                logger.error(f"Falha ao inicializar SecretManager para Key Vault '{vault_key}': {e}")
        logger.info("Todos os segredos sensíveis foram carregados do Key Vault (com fallback para env quando necessário).")
