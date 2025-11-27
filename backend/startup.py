import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env na raiz do backend
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'), override=True)

# Aqui pode-se adicionar validações de configuração, logs de inicialização, ou outras rotinas necessárias

def validate_env_vars():
    required_vars = [
        'AZURE_CLIENT_ID',
        'AZURE_TENANT_ID',
        'AZURE_CLIENT_SECRET',
        'AZURE_BLOB_CONNECTION_STRING',
        'MCP_SERVER_BASE_URL',
        'JWT_SECRET_KEY'
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise RuntimeError(f"Variáveis de ambiente obrigatórias não definidas: {', '.join(missing)}")

validate_env_vars()
