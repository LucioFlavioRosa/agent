import os
from github import Github, Repository, Auth, UnknownObjectException
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from typing import Dict, Tuple

class GitHubConnector:
    """
    Encapsula a criação e o caching de múltiplos clientes GitHub,
    selecionando o token correto e com a capacidade de criar repositórios.
    """
    _github_clients: Dict[str, Github] = {}
    _cached_repos: Dict[str, Tuple[Repository, bool]] = {} # O cache agora armazena a tupla
    _secret_client = None

    @classmethod
    def _get_secret_client(cls) -> SecretClient:
        if cls._secret_client:
            return cls._secret_client
        
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
        default_secret_name = "github-token-default"
        
        try:
            github_token = secret_client.get_secret(token_secret_name).value
        except Exception:
            print(f"AVISO: Segredo '{token_secret_name}' não encontrado. Usando token padrão.")
            github_token = secret_client.get_secret(default_secret_name).value

        auth = Auth.Token(github_token)
        new_client = Github(auth=auth)
        cls._github_clients[org_name] = new_client
        return new_client

    # --- MÉTODO PRINCIPAL CORRIGIDO E SIMPLIFICADO ---
    @classmethod
    def connection_with_info(cls, repositorio: str) -> Tuple[Repository, bool]:
        """
        Ponto de entrada principal. Obtém um objeto de repositório.
        Se o repositório não existir, ele o CRIA.
        Retorna uma tupla: (objeto_do_repo, flag_foi_criado_agora).
        """
        # Verifica o cache primeiro. Se o repo está no cache, ele não é novo.
        if repositorio in cls._cached_repos:
            print(f"Retornando o objeto do repositório '{repositorio}' do cache.")
            repo_cached, _ = cls._cached_repos[repositorio]
            return repo_cached, False # Sempre retorna False para um repo cacheado

        foi_criado_agora = False
        
        try:
            org_name, repo_name_only = repositorio.split('/')
        except ValueError:
            raise ValueError(f"O nome do repositório '{repositorio}' tem formato inválido.")

        github_client = cls._get_client_for_org(org_name)
        
        try:
            # Tenta obter o repositório. Se funcionar, ele já existe.
            print(f"Tentando acessar o repositório '{repositorio}'...")
            repo = github_client.get_repo(repositorio)
            print(f"Repositório '{repositorio}' encontrado com sucesso.")
            # 'foi_criado_agora' permanece False.
            
        except UnknownObjectException:
            # Se falhar com "Não Encontrado", CRIA o repositório.
            print(f"AVISO: Repositório '{repositorio}' não encontrado. Tentando criá-lo...")
            try:
                user = github_client.get_user()
                repo = user.create_repo(
                    name=repo_name_only,
                    description="Repositório criado automaticamente pela plataforma de agentes de IA.",
                    private=True,
                    auto_init=True
                )
                print(f"SUCESSO: Repositório '{repositorio}' criado.")
                # Somente neste caso a flag se torna True
                foi_criado_agora = True
            except GithubException as create_error:
                print(f"ERRO CRÍTICO: Falha ao criar o repositório '{repositorio}'. Erro: {create_error}")
                raise
        
        # Cacheia o resultado (o repo e a flag de criação)
        cls._cached_repos[repositorio] = (repo, foi_criado_agora)
        
        return repo, foi_criado_agora
