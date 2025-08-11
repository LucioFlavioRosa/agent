# Arquivo: tools/github_connector.py (VERSÃO FINAL CORRIGIDA)

import os
from github import Github
from github.Auth import Token
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def connection(repositorio: str):
    """
    Cria uma conexão autenticada com o GitHub e retorna o objeto do repositório E o token.
    """
    key_vault_url = os.environ["KEY_VAULT_URL"]
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=key_vault_url, credential=credential)
    github_token = client.get_secret("githubapi").value

    auth = Token(github_token)
    g = Github(auth=auth)
    repo_obj = g.get_repo(repositorio)
    
    # [CORREÇÃO] Retorna tanto o objeto do repositório quanto o token bruto
    return repo_obj, github_token
