#!/usr/bin/env python3
import os
import sys
import re
from pathlib import Path

ENV_DOC_PATH = Path('ENVIRONMENT_VARIABLES.md')
ENV_FILE_PATH = Path('.env')

URL_ENV_VARS = [
    'AZURE_KEY_VAULT_LLM_URL',
    'AZURE_KEY_VAULT_REPOSITORY_URL',
    'AZURE_KEY_VAULT_BLOB_STORAGE_URL',
    'MONGODB_CONNECTION_STRING_SECRET_NAME',
    'REDIS_URL'
]

# Variáveis obrigatórias (relatório detalhado)
REQUIRED_ENV_VARS = [
    'AZURE_KEY_VAULT_LLM_URL',
    'AZURE_KEY_VAULT_REPOSITORY_URL',
    'AZURE_KEY_VAULT_BLOB_STORAGE_URL',
    'MONGODB_CONNECTION_STRING_SECRET_NAME',
    'MONGODB_DATABASE_NAME',
    'MONGODB_COLLECTION_NAME',
    'REDIS_URL',
    'AWS_REGION',
    'AWS_ACCESS_KEY_ID',
    'AWS_SECRET_ACCESS_KEY'
]

EXAMPLES = {
    'AZURE_KEY_VAULT_LLM_URL': 'https://kv-llm-peers.vault.azure.net/',
    'AZURE_KEY_VAULT_REPOSITORY_URL': 'https://kv-repo-peers.vault.azure.net/',
    'AZURE_KEY_VAULT_BLOB_STORAGE_URL': 'https://kv-blob-peers.vault.azure.net/',
    'MONGODB_CONNECTION_STRING_SECRET_NAME': 'azure-mongodb-connection-string',
    'MONGODB_DATABASE_NAME': 'peers_db',
    'MONGODB_COLLECTION_NAME': 'user_group_mapping',
    'REDIS_URL': 'redis://peers-redis:6379',
    'AWS_REGION': 'us-east-1',
    'AWS_ACCESS_KEY_ID': 'AWS-ACCESS-KEY-ID-grupo-peers',
    'AWS_SECRET_ACCESS_KEY': 'AWS-SECRET-ACCESS-KEY-grupo-peers'
}

# Função para ler variáveis do .env
def read_env_file(env_path):
    env_vars = {}
    if env_path.exists():
        with env_path.open() as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars

# Função para validar formato de URLs
def is_valid_url(url):
    return url.startswith('https://') or url.startswith('redis://')

# Relatório detalhado
def print_detailed_report():
    print('=== Variáveis de Ambiente Obrigatórias ===')
    for var in REQUIRED_ENV_VARS:
        print(f'- {var} (Exemplo: {EXAMPLES.get(var, "<valor>")})')
    print('\n=== Variáveis que Devem Estar nos Cofres (Azure Key Vault) ===')
    print('- Secrets AWS:')
    print('  - AWS-ACCESS-KEY-ID-grupo-peers')
    print('  - AWS-SECRET-ACCESS-KEY-grupo-peers')
    print('  - AWS-REGION-grupo-peers')
    print('- MongoDB Connection String:')
    print('  - azure-mongodb-connection-string')
    print('- Tokens OpenAI:')
    print('  - openai-token-grupo-peers')
    print('- Tokens Repositórios:')
    print('  - github-token-grupo-peers')
    print('  - gitlab-token-grupo-peers')
    print('  - azure-token-grupo-peers')
    print('- Blob Storage:')
    print('  - azure-storage-connection-string-grupo-peers')
    print('\n=== Padrão de Nomenclatura dos Secrets ===')
    print('nome-grupo-empresa (Exemplo: github-token-grupo-peers)')
    print('\n=== Observação ===')
    print('O grupo é obtido via consulta ao MongoDB pelo serviço MongoDBGroupResolverService.')

# Validação principal
if __name__ == "__main__":
    env_vars = dict(os.environ)
    env_file_vars = read_env_file(ENV_FILE_PATH)
    missing_vars = []
    format_errors = []

    print_detailed_report()

    for var in REQUIRED_ENV_VARS:
        value = env_vars.get(var) or env_file_vars.get(var)
        if not value:
            missing_vars.append(var)
        else:
            if var in URL_ENV_VARS and not is_valid_url(value):
                format_errors.append(f"Formato inválido para {var}: {value}")

    if missing_vars:
        print('\n[ERRO] Variáveis de ambiente ausentes:')
        for var in missing_vars:
            print(f'- {var}')
    if format_errors:
        print('\n[ERRO] Problemas de formato:')
        for err in format_errors:
            print(f'- {err}')

    if missing_vars or format_errors:
        sys.exit(1)
    print('\n[OK] Todas as variáveis de ambiente obrigatórias estão presentes e válidas.')
    sys.exit(0)
