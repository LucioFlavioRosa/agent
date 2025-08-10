# Arquivo: tools/github_connector.py (VERSÃO CORRETA E COMPLETA)

import os
from github import Github
from github.Auth import Token
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def connection(repositorio: str):
    """
    Cria uma conexão autenticada com um repositório específico do GitHub.
    """
    # Esta função busca o token e retorna o objeto do repositório
    key_vault_url = os.environ["KEY_VAULT_URL"]
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=key_vault_url, credential=credential)
    github_token = client.get_secret("githubapi").value

    auth = Token(github_token)
    g = Github(auth=auth)
    return g.get_repo(repositorio)

# [GARANTA QUE ESTA FUNÇÃO ESTEJA AQUI]
# O erro acontece porque esta função está faltando no seu arquivo.
def get_github_token() -> str:
    """
    Busca apenas o valor do token do GitHub a partir do Azure Key Vault.
    """
    try:
        key_vault_url = os.environ["KEY_VAULT_URL"]
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=key_vault_url, credential=credential)
        github_token = client.get_secret("githubapi").value
        if not github_token:
            raise ValueError("Token do GitHub encontrado no Key Vault está vazio.")
        return github_token
    except Exception as e:
        print(f"ERRO CRÍTICO ao buscar token do GitHub do Key Vault: {e}")
        raise
