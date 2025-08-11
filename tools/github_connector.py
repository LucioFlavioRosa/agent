# Arquivo: tools/github_connector.py (VERSÃO API-PURA)

import os
from github import Github
from github.Auth import Token
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def connection(repositorio: str):
    """
    Cria uma conexão autenticada com um repositório específico do GitHub
    e retorna o objeto do repositório.
    """
    key_vault_url = os.environ["KEY_VAULT_URL"]
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=key_vault_url, credential=credential)
    github_token = client.get_secret("githubapi").value

    auth = Token(github_token)
    g = Github(auth=auth)
    return g.get_repo(repositorio)
