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
    
    def _is_project_id(self, repository_name: str) -> bool:
        try:
            int(repository_name)
            return True
        except ValueError:
            return False
    
    def _normalize_project_identifier(self, repository_name: str) -> str:
        if self._is_project_id(repository_name):
            return str(repository_name).strip()
        else:
            return repository_name.strip()
    
    def get_repository(self, repository_name: str, token: str) -> any:
        normalized_identifier = self._normalize_project_identifier(repository_name)
        print(f"[GitLab Provider] Tentando acessar o projeto: '{normalized_identifier}'")
        
        try:
            gl = gitlab.Gitlab(url="https://gitlab.com", private_token=token)
            gl.auth()
            print(f"[GitLab Provider] Autenticação GitLab bem-sucedida.")
        except gitlab.exceptions.GitlabAuthenticationError as e:
            print(f"[GitLab Provider] ERRO: Token de autenticação inválido.")
            raise ValueError("Token de autenticação do GitLab é inválido.") from e
        except Exception as e:
            raise RuntimeError(f"Erro inesperado ao inicializar cliente GitLab: {e}")
    
        try:
            if self._is_project_id(normalized_identifier):
                project_id = int(normalized_identifier)
                print(f"[GitLab Provider] Detectado Project ID numérico: {project_id} (formato mais robusto)")
                project = gl.projects.get(project_id)
                print(f"[GitLab Provider] Projeto encontrado por ID: '{project.name_with_namespace}' (ID: {project.id}).")
            else:
                print(f"[GitLab Provider] Detectado path completo: {normalized_identifier}")
                project = gl.projects.get(normalized_identifier)
                print(f"[GitLab Provider] Projeto '{project.name_with_namespace}' encontrado com sucesso (ID: {project.id}).")
            
            if not hasattr(project, 'default_branch'):
                default_branch = project.attributes.get('default_branch', 'main')
                project.default_branch = default_branch
                print(f"[GitLab Provider] Branch padrão definida: {default_branch}")
            
            return project
            
        except gitlab.exceptions.GitlabGetError as e:
            if e.response_code == 404:
                if self._is_project_id(normalized_identifier):
                    print(f"[GitLab Provider] ERRO: Projeto com ID '{normalized_identifier}' não encontrado (404).")
                    raise ValueError(f"Projeto GitLab com ID '{normalized_identifier}' não encontrado. Verifique se o ID está correto e se o token tem acesso a ele.")
                else:
                    print(f"[GitLab Provider] ERRO: Projeto '{normalized_identifier}' não encontrado (404).")
                    raise ValueError(f"Repositório GitLab '{normalized_identifier}' não encontrado. Verifique o nome e se o token tem acesso a ele.")
            elif e.response_code == 403:
                print(f"[GitLab Provider] ERRO: Acesso negado ao projeto '{normalized_identifier}' (403).")
                raise ValueError(f"Acesso negado ao repositório '{normalized_identifier}'. Verifique as permissões do token.")
            else:
                raise RuntimeError(f"Erro da API do GitLab ao buscar repositório ({e.response_code}): {e}")
        except Exception as e:
            raise RuntimeError(f"Erro inesperado ao buscar o projeto GitLab '{normalized_identifier}': {e}") from e
        
    def create_repository(self, repository_name: str, token: str, description: str = "", private: bool = True) -> Project:
        normalized_identifier = self._normalize_project_identifier(repository_name)
        print(f"[GitLab Provider] Tentando criar repositório: {normalized_identifier}")
        
        if self._is_project_id(normalized_identifier):
            raise ValueError(
                f"ERRO: Não é possível criar repositório usando Project ID '{normalized_identifier}'. "
                "Para criar um projeto GitLab, use o formato 'namespace/projeto'. "
                "Project IDs são apenas para acessar projetos existentes."
            )
        
        try:
            namespace, project_name = self._parse_repository_name(normalized_identifier)
            print(f"[GitLab Provider] Namespace para criação: {namespace}, Projeto: {project_name}")
        except ValueError as e:
            print(f"[GitLab Provider] Erro no parsing do nome: {e}")
            raise
        
        try:
            gl = gitlab.Gitlab(url="https://gitlab.com", private_token=token)
            gl.auth()
            print(f"[GitLab Provider] Autenticação para criação bem-sucedida.")
            
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
                group = gl.groups.get(namespace)
                group_name = group.attributes.get('name', namespace)
                project_data['namespace_id'] = group.id
                print(f"[GitLab Provider] Grupo encontrado: {group_name}, ID: {group.id}")
                project = gl.projects.create(project_data)
                
            except gitlab.exceptions.GitlabGetError as group_error:
                print(f"[GitLab Provider] Grupo '{namespace}' não encontrado ou sem permissão ({group_error.response_code}), criando como projeto pessoal")
                if 'namespace_id' in project_data:
                    del project_data['namespace_id']
                project = gl.projects.create(project_data)
                print(f"[GitLab Provider] Projeto criado como pessoal devido à falta de acesso ao grupo '{namespace}'")
            
            if not hasattr(project, 'default_branch'):
                project.default_branch = 'main'
            
            print(f"[GitLab Provider] Projeto criado com sucesso: {project.web_url} (ID: {project.id})")
            return project
            
        except gitlab.exceptions.GitlabCreateError as e:
            print(f"[GitLab Provider] Erro de criação: {e}")
            if "has already been taken" in str(e):
                raise ValueError(f"Projeto '{normalized_identifier}' já existe no GitLab.")
            else:
                raise ValueError(f"Erro ao criar projeto '{normalized_identifier}': {e}")
        except gitlab.exceptions.GitlabAuthenticationError as e:
            print(f"[GitLab Provider] Erro de autenticação na criação: {e}")
            raise ValueError(f"Token de autenticação inválido para criar projeto '{normalized_identifier}'.")
        except Exception as e:
            print(f"[GitLab Provider] Erro inesperado na criação: {type(e).__name__}: {e}")
            raise ValueError(f"Erro inesperado ao criar projeto '{normalized_identifier}': {e}") from e