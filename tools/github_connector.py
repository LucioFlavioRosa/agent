import os
from github import Github, Repository, Auth, UnknownObjectException
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from typing import Dict, Tuple, Any

class GitHubConnector:
    """
    Encapsula a criação e o caching de múltiplos clientes GitHub,
    selecionando o token correto e com a capacidade de criar repositórios.
    """
    _github_clients: Dict[str, Github] = {}
    _cached_repos: Dict[str, Repository] = {}
    _secret_client = None
    _repo_metadata: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def _get_secret_client(cls) -> SecretClient:
        if cls._secret_client:
            return cls._secret_client
        print("Conectando ao Azure Key Vault pela primeira vez...")
        key_vault_url = os.environ["KEY_VAULT_URL"]
        credential = DefaultAzureCredential()
        cls._secret_client = SecretClient(vault_url=key_vault_url, credential=credential)
        return cls._secret_client

    @classmethod
    def _get_client_for_org(cls, org_name: str) -> Github:
        if org_name in cls._github_clients:
            return cls._github_clients[org_name]
        secret_client = cls._get_secret_client()
        token_secret_name = f"github-token-{org_name}"
        try:
            github_token = secret_client.get_secret(token_secret_name).value
        except Exception:
            print(f"AVISO: Segredo '{token_secret_name}' não encontrado. Usando token padrão.")
        auth = Auth.Token(github_token)
        new_client = Github(auth=auth)
        cls._github_clients[org_name] = new_client
        return new_client

    @classmethod
    def connection(cls, repositorio: str, return_info: bool = False) -> Any:
        """
        Ponto de entrada principal. Obtém um objeto de repositório.
        Se o repositório não existir, ele o CRIA.
        Se return_info=True, retorna (repo, metadata_dict) onde metadata_dict tem 'is_novo_repo'.
        """
        if repositorio in cls._cached_repos:
            print(f"Retornando o objeto do repositório '{repositorio}' do cache.")
            repo = cls._cached_repos[repositorio]
            metadata = cls._repo_metadata.get(repositorio, {"is_novo_repo": False})
            return (repo, metadata) if return_info else repo
        try:
            org_name, repo_name_only = repositorio.split('/')
        except ValueError:
            raise ValueError(f"O nome do repositório '{repositorio}' tem formato inválido. Esperado 'organizacao/repositorio'.")
        github_client = cls._get_client_for_org(org_name)
        is_novo_repo = False
        try:
            print(f"Tentando acessar o repositório '{repositorio}'...")
            repo = github_client.get_repo(repositorio)
            print(f"Repositório '{repositorio}' encontrado com sucesso.")
        except UnknownObjectException:
            print(f"AVISO: Repositório '{repositorio}' não encontrado. Tentando criá-lo...")
            try:
                org = github_client.get_organization(org_name)
                repo = org.create_repo(
                    name=repo_name_only,
                    description="Repositório criado automaticamente pela plataforma de agentes de IA.",
                    private=True,
                    auto_init=True
                )
                print(f"SUCESSO: Repositório '{repositorio}' criado.")
                is_novo_repo = True
            except UnknownObjectException:
                print(f"AVISO: Organização '{org_name}' não encontrada. Tentando criar o repositório na conta do usuário autenticado.")
                user = github_client.get_user()
                repo = user.create_repo(
                    name=repo_name_only,
                    description="Repositório criado automaticamente pela plataforma de agentes de IA.",
                    private=True,
                    auto_init=True
                )
                print(f"SUCESSO: Repositório '{repositorio}' criado na conta do usuário.")
                is_novo_repo = True
            except Exception as create_error:
                print(f"ERRO CRÍTICO: Falha ao criar o repositório '{repositorio}'. Verifique as permissões do token. Erro: {create_error}")
                raise
        cls._cached_repos[repositorio] = repo
        cls._repo_metadata[repositorio] = {"is_novo_repo": is_novo_repo}
        return (repo, {"is_novo_repo": is_novo_repo}) if return_info else repo

    @classmethod
    def is_novo_repo(cls, repositorio: str) -> bool:
        """
        Retorna True se o repositório foi recém-criado nesta execução.
        """
        return cls._repo_metadata.get(repositorio, {}).get("is_novo_repo", False)
