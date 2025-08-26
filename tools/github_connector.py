import os
from github import Github, Repository, Auth, UnknownObjectException
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from typing import Dict
import importlib

class GitHubConnector:
    """
    Encapsula a criação e o caching de múltiplos clientes GitHub,
    selecionando o token correto e com a capacidade de criar repositórios.
    """
    _github_clients: Dict[str, Github] = {}
    _cached_repos: Dict[str, Repository] = {}
    _secret_client = None

    @classmethod
    def _get_secret_client(cls) -> SecretClient:
        # (Esta função auxiliar não muda)
        if cls._secret_client:
            return cls._secret_client
        
        print("Conectando ao Azure Key Vault pela primeira vez...")
        key_vault_url = os.environ["KEY_VAULT_URL"]
        credential = DefaultAzureCredential()
        cls._secret_client = SecretClient(vault_url=key_vault_url, credential=credential)
        return cls._secret_client

    @classmethod
    def _get_client_for_org(cls, org_name: str) -> Github:
        # (Esta função auxiliar não muda)
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
    def connection(cls, repositorio: str) -> Repository:
        """
        Ponto de entrada principal. Obtém um objeto de repositório.
        Se o repositório não existir, ele o CRIA.
        """
        if repositorio in cls._cached_repos:
            print(f"Retornando o objeto do repositório '{repositorio}' do cache.")
            return cls._cached_repos[repositorio]

        try:
            org_name, repo_name_only = repositorio.split('/')
        except ValueError:
            raise ValueError(f"O nome do repositório '{repositorio}' tem formato inválido. Esperado 'organizacao/repositorio'.")

        github_client = cls._get_client_for_org(org_name)
        
        try:
            # --- MUDANÇA: LÓGICA "GET OR CREATE" ---
            # 1. Tenta obter o repositório.
            print(f"Tentando acessar o repositório '{repositorio}'...")
            repo = github_client.get_repo(repositorio)
            print(f"Repositório '{repositorio}' encontrado com sucesso.")
            
        except UnknownObjectException:
            # 2. Se falhar com "Não Encontrado" (404), cria o repositório.
            print(f"AVISO: Repositório '{repositorio}' não encontrado. Tentando criá-lo...")
            try:
                # Tenta obter a organização para criar o repo dentro dela
                org = github_client.get_organization(org_name)
                repo = org.create_repo(
                    name=repo_name_only,
                    description="Repositório criado automaticamente pela plataforma de agentes de IA.",
                    private=True, # Mude para False se quiser repositórios públicos
                    auto_init=True # Cria o repo com um README inicial, essencial para poder criar branches
                )
                print(f"SUCESSO: Repositório '{repositorio}' criado.")
            except UnknownObjectException:
                # Se a "organização" for na verdade um usuário
                print(f"AVISO: Organização '{org_name}' não encontrada. Tentando criar o repositório na conta do usuário autenticado.")
                user = github_client.get_user()
                repo = user.create_repo(
                    name=repo_name_only,
                    description="Repositório criado automaticamente pela plataforma de agentes de IA.",
                    private=True,
                    auto_init=True
                )
                print(f"SUCESSO: Repositório '{repositorio}' criado na conta do usuário.")
            except Exception as create_error:
                print(f"ERRO CRÍTICO: Falha ao criar o repositório '{repositorio}'. Verifique as permissões do token. Erro: {create_error}")
                raise
        
        # 3. Cacheia e retorna o objeto do repositório (existente ou recém-criado).
        cls._cached_repos[repositorio] = repo
        return repo
