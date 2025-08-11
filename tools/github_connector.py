# Arquivo: tools/github_connector.py (VERSÃO CORRIGIDA E FINAL)

import os
from github import Github
from github.Auth import Token
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def _get_essentials():
    """Função auxiliar interna para buscar o token e criar a conexão base."""
    key_vault_url = os.environ["KEY_VAULT_URL"]
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=key_vault_url, credential=credential)
    github_token = client.get_secret("githubapi").value
    if not github_token:
        raise ValueError("Token do GitHub encontrado no Key Vault está vazio.")
    
    auth = Token(github_token)
    g = Github(auth=auth)
    return g, github_token

def get_authenticated_repo(repositorio: str):
    """
    USADO PARA LEITURA: Retorna apenas o objeto do repositório autenticado.
    """
    g, _ = _get_essentials()
    return g.get_repo(repositorio)

def get_repo_and_token(repositorio: str):
    """
    USADO PARA ESCRITA/COMMIT: Retorna o objeto do repositório E o token bruto.
    """
    g, github_token = _get_essentials()
    repo_obj = g.get_repo(repositorio)
    return repo_obj, github_token
