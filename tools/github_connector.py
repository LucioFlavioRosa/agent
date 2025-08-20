import os
from github import Github, Repository
from github.Auth import Token
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

class GitHubConnector:
    """
    Encapsula a criação e caching do cliente GitHub. Interface IGitHubRepository será criada em etapa futura.
    """
    _github_client = None
    _cached_repos = {}

    @classmethod
    def get_github_client(cls) -> Github:
        if cls._github_client:
            return cls._github_client
        print("Conectando ao Azure Key Vault para obter o token do GitHub (operação única)...")
        try:
            key_vault_url = os.environ["KEY_VAULT_URL"]
        except KeyError:
            raise EnvironmentError("ERRO: A variável de ambiente KEY_VAULT_URL não foi configurada.")
        credential = DefaultAzureCredential()
        secret_client = SecretClient(vault_url=key_vault_url, credential=credential)
        try:
            github_token = secret_client.get_secret("githubapi").value
        except Exception as e:
            print(f"ERRO: Falha ao obter o segredo 'githubapi' do Key Vault: {e}")
            raise
        auth = Token(github_token)
        cls._github_client = Github(auth=auth)
        print("Cliente GitHub autenticado e cacheado com sucesso.")
        return cls._github_client

    @classmethod
    def connection(cls, repositorio: str) -> Repository:
        if repositorio in cls._cached_repos:
            print(f"Retornando o objeto do repositório '{repositorio}' do cache.")
            return cls._cached_repos[repositorio]
        g = cls.get_github_client()
        print(f"Acessando o repositório '{repositorio}' pela primeira vez...")
        repo = g.get_repo(repositorio)
        cls._cached_repos[repositorio] = repo
        return repo
