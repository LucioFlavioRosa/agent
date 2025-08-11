# Arquivo: tools/github_connector.py (VERSÃO OTIMIZADA E ROBUSTA)

import os
from github import Github, Repository
from github.Auth import Token
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# --- [NOVO] Seção de Caching em Memória ---
# Estes objetos serão criados apenas uma vez e reutilizados nas chamadas seguintes.
_github_client: Github | None = None
_cached_repos: dict[str, Repository.Repository] = {}

def get_github_client() -> Github:
    """
    Função interna para criar e cachear o cliente principal do GitHub.
    Evita chamar o Key Vault repetidamente.
    """
    global _github_client
    if _github_client:
        return _github_client

    print("Conectando ao Azure Key Vault para obter o token do GitHub (operação única)...")
    try:
        key_vault_url = os.environ["KEY_VAULT_URL"]
    except KeyError:
        # Erro mais claro se a variável de ambiente não for definida
        raise EnvironmentError("ERRO: A variável de ambiente KEY_VAULT_URL não foi configurada.")

    credential = DefaultAzureCredential()
    secret_client = SecretClient(vault_url=key_vault_url, credential=credential)
    
    try:
        github_token = secret_client.get_secret("githubapi").value
    except Exception as e:
        # Erro mais claro se o segredo não for encontrado
        print(f"ERRO: Falha ao obter o segredo 'githubapi' do Key Vault: {e}")
        raise

    auth = Token(github_token)
    _github_client = Github(auth=auth)
    print("Cliente GitHub autenticado e cacheado com sucesso.")
    return _github_client


def connection(repositorio: str) -> Repository.Repository:
    """
    Cria uma conexão autenticada com um repositório específico do GitHub
    e retorna o objeto do repositório, utilizando cache para performance.
    
    :param repositorio: O nome completo do repositório (ex: "meu_usuario/meu_projeto").
    """
    # Verifica se o objeto do repositório já está no cache
    if repositorio in _cached_repos:
        print(f"Retornando o objeto do repositório '{repositorio}' do cache.")
        return _cached_repos[repositorio]

    # Se não estiver no cache, obtém o cliente principal (que também usa cache)
    g = get_github_client()
    
    # Obtém o objeto do repositório e o armazena no cache
    print(f"Acessando o repositório '{repositorio}' pela primeira vez...")
    repo = g.get_repo(repositorio)
    _cached_repos[repositorio] = repo
    
    return repo
