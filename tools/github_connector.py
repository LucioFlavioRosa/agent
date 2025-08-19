import os
from github import Github, Repository
from github.Auth import Token
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from typing import Dict

class GitHubConnector:
    """
    Encapsula a criação e o caching de múltiplos clientes GitHub,
    selecionando o token de autenticação correto com base na organização do repositório.
    """
    _github_clients: Dict[str, Github] = {}
    _cached_repos: Dict[str, Repository] = {}
    _secret_client = None

    @classmethod
    def _get_secret_client(cls) -> SecretClient:
        """Cria e cacheia um cliente para o Azure Key Vault."""
        if cls._secret_client:
            return cls._secret_client
        
        print("Conectando ao Azure Key Vault pela primeira vez...")
        try:
            key_vault_url = os.environ["KEY_VAULT_URL"]
        except KeyError:
            raise EnvironmentError("ERRO: A variável de ambiente KEY_VAULT_URL não foi configurada.")
        
        credential = DefaultAzureCredential()
        cls._secret_client = SecretClient(vault_url=key_vault_url, credential=credential)
        return cls._secret_client

    @classmethod
    def _get_client_for_org(cls, org_name: str) -> Github:
        """
        Obtém um cliente GitHub autenticado para uma organização específica.
        Busca o token no Key Vault e cacheia o cliente para reutilização.
        """
        if org_name in cls._github_clients:
            return cls._github_clients[org_name]

        print(f"Buscando token para a organização '{org_name}' no Key Vault...")
        secret_client = cls._get_secret_client()
        
        token_secret_name = f"github-token-{org_name}"
        default_secret_name = "github-token-default"
        
        try:
            github_token = secret_client.get_secret(token_secret_name).value
            print(f"Token específico para '{org_name}' encontrado.")
        except Exception:
            print(f"AVISO: Segredo '{token_secret_name}' não encontrado. Usando o token padrão '{default_secret_name}'.")
            try:
                github_token = secret_client.get_secret(default_secret_name).value
            except Exception as e:
                raise RuntimeError(f"Falha ao obter o segredo padrão '{default_secret_name}' do Key Vault: {e}")

        auth = Token(github_token)
        new_client = Github(auth=auth)
        cls._github_clients[org_name] = new_client
        print(f"Novo cliente GitHub para '{org_name}' autenticado e cacheado.")
        return new_client

    @classmethod
    def connection(cls, repositorio: str) -> Repository:
        """
        Ponto de entrada principal. Obtém um objeto de repositório, garantindo
        que o cliente GitHub correto seja usado para a organização do repositório.
        """
        if repositorio in cls._cached_repos:
            return cls._cached_repos[repositorio]

        try:
            org_name = repositorio.split('/')[0]
        except IndexError:
            raise ValueError(f"O nome do repositório '{repositorio}' tem formato inválido. Esperado 'organizacao/repositorio'.")

        github_client = cls._get_client_for_org(org_name)
        
        print(f"Acessando o repositório '{repositorio}' com o cliente da organização '{org_name}'...")
        repo = github_client.get_repo(repositorio)
        
        cls._cached_repos[repositorio] = repo
        return repo
