import gitlab
from gitlab.v4.objects import Project
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from typing import Any

class GitLabRepositoryProvider(IRepositoryProvider):
    
    def _parse_repository_name(self, repository_name: str) -> tuple:
        parts = repository_name.split('/')
        if len(parts) < 2:
            raise ValueError(f"Nome do repositório '{repository_name}' tem formato inválido. Esperado 'namespace/projeto' ou 'grupo/subgrupo/projeto'.")
        
        if len(parts) == 2:
            return parts[0], parts[1]
        else:
            namespace = '/'.join(parts[:-1])
            project = parts[-1]
            return namespace, project
    
    def get_repository(self, repository_name: str, token: str, project_id: str = None) -> any:
        print(f"[GitLab Provider] Tentando acessar o projeto: '{repository_name}'")
        if project_id:
            print(f"[GitLab Provider] Project ID fornecido: {project_id} - priorizando busca por ID")
        
        try:
            gl = gitlab.Gitlab(url="https://gitlab.com", private_token=token)
            gl.auth()
        except gitlab.exceptions.GitlabAuthenticationError as e:
            print(f"[GitLab Provider] ERRO: Token de autenticação inválido.")
            raise ValueError("Token de autenticação do GitLab é inválido.") from e
        except Exception as e:
            raise RuntimeError(f"Erro inesperado ao inicializar cliente GitLab: {e}")
    
        try:
            if project_id:
                print(f"[GitLab Provider] Buscando projeto por ID: {project_id}")
                project = gl.projects.get(project_id)
                print(f"[GitLab Provider] Projeto encontrado por ID: '{project.name_with_namespace}' (ID: {project.id}).")
            else:
                print(f"[GitLab Provider] Buscando projeto por nome: {repository_name}")
                project = gl.projects.get(repository_name)
                print(f"[GitLab Provider] Projeto '{project.name_with_namespace}' encontrado com sucesso (ID: {project.id}).")
            
            if not hasattr(project, 'default_branch'):
                project.default_branch = project.attributes.get('default_branch', 'main')
            
            return project
            
        except gitlab.exceptions.GitlabGetError as e:
            if e.response_code == 404:
                identifier = project_id if project_id else repository_name
                print(f"[GitLab Provider] ERRO: Projeto '{identifier}' não encontrado (404).")
                raise ValueError(f"Repositório GitLab '{identifier}' não encontrado. Verifique o nome/ID e se o token tem acesso a ele.")
            elif e.response_code == 403:
                identifier = project_id if project_id else repository_name
                print(f"[GitLab Provider] ERRO: Acesso negado ao projeto '{identifier}' (403).")
                raise ValueError(f"Acesso negado ao repositório '{identifier}'. Verifique as permissões do token.")
            else:
                raise RuntimeError(f"Erro da API do GitLab ao buscar repositório ({e.response_code}): {e}")
        except Exception as e:
            identifier = project_id if project_id else repository_name
            raise RuntimeError(f"Erro inesperado ao buscar o projeto GitLab '{identifier}': {e}") from e
        
    def create_repository(self, repository_name: str, token: str, description: str = "", private: bool = True, project_id: str = None) -> Project:
        print(f"[GitLab Provider] Tentando criar repositório: {repository_name}")
        
        try:
            namespace, project_name = self._parse_repository_name(repository_name)
            print(f"[GitLab Provider] Namespace para criação: {namespace}, Projeto: {project_name}")
        except ValueError as e:
            print(f"[GitLab Provider] Erro no parsing do nome: {e}")
            raise
        
        try:
            gl = gitlab.Gitlab(url="https://gitlab.com", private_token=token)
            
            project_data = {
                'name': project_name,
                'path': project_name,
                'description': description or "Projeto criado automaticamente pela plataforma de agentes de IA.",
                'visibility': 'private' if private else 'public',
                'initialize_with_readme': True,
                'default_branch': 'main'
            }
            
            print(f"[GitLab Provider] Tentando criar em namespace/grupo: {namespace}")
            try:
                group = gl.groups.get(namespace, lazy=True)
                group_info = group.name
                project_data['namespace_id'] = group.id
                print(f"[GitLab Provider] Grupo encontrado: {group_info}, ID: {group.id}")
                project = gl.projects.create(project_data)
                
            except gitlab.exceptions.GitlabGetError as group_error:
                print(f"[GitLab Provider] Grupo não encontrado ({group_error.response_code}), criando como projeto pessoal")
                if 'namespace_id' in project_data:
                    del project_data['namespace_id']
                project = gl.projects.create(project_data)
            
            if not hasattr(project, 'default_branch'):
                project.default_branch = 'main'
            
            print(f"[GitLab Provider] Projeto criado com sucesso: {project.web_url}")
            return project
            
        except gitlab.exceptions.GitlabCreateError as e:
            print(f"[GitLab Provider] Erro de criação: {e}")
            if "has already been taken" in str(e):
                raise ValueError(f"Projeto '{repository_name}' já existe no GitLab.")
            else:
                raise ValueError(f"Erro ao criar projeto '{repository_name}': {e}")
        except gitlab.exceptions.GitlabAuthenticationError as e:
            print(f"[GitLab Provider] Erro de autenticação na criação: {e}")
            raise ValueError(f"Token de autenticação inválido para criar projeto '{repository_name}'.")
        except Exception as e:
            print(f"[GitLab Provider] Erro inesperado na criação: {type(e).__name__}: {e}")
            raise ValueError(f"Erro inesperado ao criar projeto '{repository_name}': {e}") from e