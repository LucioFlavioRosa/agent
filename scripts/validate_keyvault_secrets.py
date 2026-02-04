#!/usr/bin/env python3
import sys
import os
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# Secrets essenciais (não contextualizados por usuário)
REQUIRED_SECRETS = [
    'azure-storage-connection-string',
    'AWS-ACCESS-KEY-ID-grupo-peers',
    'AWS-SECRET-ACCESS-KEY-grupo-peers',
    'AWS-REGION-grupo-peers',
    'openai-token-grupo-peers',
    'github-token-grupo-peers',
    'gitlab-token-grupo-peers',
    'azure-token-grupo-peers'
]

# URLs dos cofres
VAULT_URLS = [
    os.environ.get('AZURE_KEY_VAULT_LLM_URL'),
    os.environ.get('AZURE_KEY_VAULT_REPOSITORY_URL'),
    os.environ.get('AZURE_KEY_VAULT_BLOB_STORAGE_URL')
]

def validate_secrets():
    credential = DefaultAzureCredential()
    found_secrets = set()
    missing_secrets = set(REQUIRED_SECRETS)
    for vault_url in VAULT_URLS:
        if not vault_url:
            print(f'[ERRO] URL do Key Vault não definida: {vault_url}')
            continue
        try:
            client = SecretClient(vault_url=vault_url, credential=credential)
            secret_properties = client.list_properties_of_secrets()
            secrets_in_vault = set([s.name for s in secret_properties])
            found = secrets_in_vault & missing_secrets
            found_secrets.update(found)
            missing_secrets -= found
            print(f'Key Vault: {vault_url}')
            print(f'  Secrets encontrados: {sorted(found)}')
        except Exception as e:
            print(f'[ERRO] Falha ao conectar ao Key Vault {vault_url}: {e}')
    if missing_secrets:
        print('\n[ERRO] Secrets ausentes:')
        for s in sorted(missing_secrets):
            print(f'- {s}')
        sys.exit(1)
    print('\n[OK] Todos os secrets essenciais foram encontrados nos Key Vaults.')
    sys.exit(0)

if __name__ == "__main__":
    validate_secrets()
