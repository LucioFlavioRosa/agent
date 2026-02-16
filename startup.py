import os
from dotenv import load_dotenv
import logging

# Carrega variáveis de ambiente do arquivo .env na raiz do backend
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'), override=True)

from backend.app.services.config_loader_service import ConfigLoaderService

# Aqui pode-se adicionar validações de configuração, logs de inicialização, ou outras rotinas necessárias

def validate_env_vars():
    required_vars = [
        'KEY_VAULT_URL',
        'REDIS_PERM_TTL'
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        logging.error(f"Variável de ambiente obrigatória não definida: {', '.join(missing)}")
        raise RuntimeError(f"Variável de ambiente obrigatória não definida: {', '.join(missing)}")
    else:
        logging.info("Variável de ambiente KEY_VAULT_URL está definida.")

# Carrega segredos sensíveis do Key Vault antes de inicializar endpoints
try:
    ConfigLoaderService().load_secrets_from_key_vault()
    logging.info("Segredos sensíveis carregados do Key Vault com sucesso.")
except Exception as e:
    logging.error(f"Erro ao carregar segredos do Key Vault na inicialização: {e}")
    logging.warning("Inicializando em modo degradado: apenas variáveis de ambiente locais serão usadas.")

validate_env_vars()
