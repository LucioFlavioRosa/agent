from github import Github, Repository, Auth, UnknownObjectException
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from typing import Any

class GitHubRepositoryProvider(IRepositoryProvider):
    """
    Implementação do provedor de repositório para GitHub.
    Responsabilidade única: interagir com a API do GitHub.
    Esta versão é mais eficiente e robusta.
    """
    def __init__(self, token: str):
        """
        O cliente do GitHub é inicializado UMA VEZ aqui para ser reutilizado.
        Isso é muito mais eficiente do que criar uma nova conexão a cada chamada.
        """
        try:
            auth = Auth.Token(token)
            self.client = Github(auth=auth)
            # Verifica se a autenticação foi bem-sucedida
            self.authenticated_user = self.client.get_user()
            print(f"[GitHub Provider] Autenticado com sucesso como: {self.authenticated_user.login}")
        except Exception as e:
            raise ConnectionError(f"Falha ao autenticar com o GitHub. Verifique o token. Erro: {e}") from e

    def get_repository(self, repository_name: str, token: str = None) -> Repository:
        """
        Obtém um repositório existente do GitHub.
        O parâmetro 'token' é ignorado, pois a conexão já foi estabelecida.
        """
        try:
            return self.client.get_repo(repository_name)
        except UnknownObjectException as e:
            raise ValueError(f"Repositório '{repository_name}' não encontrado ou acesso negado.") from e
        except Exception as e:
            raise RuntimeError(f"Erro inesperado ao acessar repositório '{repository_name}': {e}") from e

    def create_repository(self, repository_name: str, token: str = None, description: str = "", private: bool = True) -> Repository:
        """
        Cria um novo repositório no GitHub de forma explícita,
        verificando se o dono é uma Organização ou um Usuário.
        """
        owner_login, repo_name_only = self._parse_repository_name(repository_name)

        try:
            # Busca o dono (seja usuário ou organização) para determinar o tipo
            owner = self.client.get_user(owner_login)
            
            repo_data = {
                "name": repo_name_only,
                "description": description or "Repositório criado automaticamente.",
                "private": private,
                "auto_init": True
            }

            print(f"[GitHub Provider] Tentando criar '{repo_name_only}' sob o dono '{owner.login}' (Tipo: {owner.type})")

            # Lógica explícita baseada no tipo do dono
            if owner.type == "Organization":
                # Se for uma organização, usa o método de criação da organização
                return owner.create_repo(**repo_data)
            elif owner.type == "User":
                # Se for um usuário, verifica se é o usuário autenticado
                if owner.login == self.authenticated_user.login:
                    return self.authenticated_user.create_repo(**repo_data)
                else:
                    # Um usuário não pode criar um repositório para outro usuário
                    raise PermissionError(f"Você está autenticado como '{self.authenticated_user.login}', mas tentando criar um repositório para o usuário '{owner.login}'.")
            else:
                raise ValueError(f"Tipo de dono de repositório desconhecido: '{owner.type}'")
                
        except UnknownObjectException as e:
             raise ValueError(f"O dono (organização ou usuário) '{owner_login}' não foi encontrado.") from e
        except Exception as e:
            raise RuntimeError(f"Erro inesperado ao criar repositório '{repository_name}': {e}") from e

    def get_provider_type(self) -> str:
        """Retorna o nome do provedor para cumprir a interface."""
        return "github"
        
    def _parse_repository_name(self, repository_name: str) -> tuple[str, str]:
        """
        Divide 'dono/nome_repo' de forma robusta, lidando com subgrupos.
        Ex: 'org/time/projeto' -> ('org/time', 'projeto')
        """
        last_slash_index = repository_name.rfind('/')
        if last_slash_index == -1 or last_slash_index == 0 or last_slash_index == len(repository_name) - 1:
            raise ValueError(f"Nome do repositório '{repository_name}' tem formato inválido. Esperado 'dono/nome_repo'.")
        
        owner = repository_name[:last_slash_index]
        repo_name = repository_name[last_slash_index + 1:]
        return owner, repo_name
