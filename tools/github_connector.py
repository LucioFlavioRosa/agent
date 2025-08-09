import os
from github import Github
from github.Auth import Token
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


def connection(repositorio: str):
    # Obtém o URL do Key Vault das variáveis de ambiente
    key_vault_url = os.environ["KEY_VAULT_URL"]

    # Usa a identidade gerenciada para autenticar de forma automática
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=key_vault_url, credential=credential)

    # Obtém o token do GitHub do Key Vault.
    # O nome do segredo deve ser o mesmo que você configurou no Key Vault
    github_token = client.get_secret("githubapi").value

    auth = Token(github_token)
    g = Github(auth=auth)
    return g.get_repo(repositorio)

