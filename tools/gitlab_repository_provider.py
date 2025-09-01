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
    
    def get_repository(self, repository_name: str, token: str) -> Project:
        print(f"[GitLab Provider] Tentando acessar repositório: {repository_name}")
        print(f"[GitLab Provider] Token fornecido: {'***' + token[-4:] if len(token) > 4 else '***'}")
        
        try:
            namespace, project_name = self._parse_repository_name(repository_name)
            print(f"[GitLab Provider] Namespace: {namespace}, Projeto: {project_name}")
            
            gl = gitlab.Gitlab(url="https://gitlab.com", private_token=token)
            
            print(f"[GitLab Provider] Testando autenticação...")
            try:
                user = gl.auth()
                print(f"[GitLab Provider] Autenticação bem-sucedida para usuário: {user.get('username', 'N/A')}")
            except Exception as auth_error:
                print(f"[GitLab Provider] AVISO: Falha na validação de autenticação: {auth_error}")
            
            print(f"[GitLab Provider] Buscando projeto por path: {repository_name}")
            project = gl.projects.get(repository_name, lazy=True)
            
            print(f"[GitLab Provider] Validando existência do projeto...")
            try:
                project_info = project.name
                print(f"[GitLab Provider] Projeto encontrado: {project_info}")
            except gitlab.exceptions.GitlabGetError as get_error:
                if get_error.response_code == 404:
                    print(f"[GitLab Provider] Projeto '{repository_name}' não encontrado (404)")
                    raise ValueError(f"Projeto '{repository_name}' não encontrado no GitLab.")
                elif get_error.response_code == 403:
                    print(f"[GitLab Provider] Acesso negado ao projeto '{repository_name}' (403)")
                    raise ValueError(f"Acesso negado ao projeto '{repository_name}'. Verifique as permissões do token.")
                else:
                    print(f"[GitLab Provider] Erro HTTP {get_error.response_code} ao acessar projeto")
                    raise ValueError(f"Erro ao acessar projeto '{repository_name}': {get_error}")
            
            if not hasattr(project, 'default_branch'):
                try:
                    project.default_branch = project.default_branch or 'main'
                    print(f"[GitLab Provider] Branch padrão definida: {project.default_branch}")
                except:
                    project.default_branch = 'main'
                    print(f"[GitLab Provider] Branch padrão definida como fallback: main")
            
            print(f"[GitLab Provider] Projeto configurado com sucesso")
            return project
            
        except gitlab.exceptions.GitlabGetError as e:
            print(f"[GitLab Provider] Erro GitlabGetError: {e.response_code} - {e}")
            if e.response_code == 404:
                raise ValueError(f"Projeto '{repository_name}' não encontrado no GitLab.")
            elif e.response_code == 403:
                raise ValueError(f"Acesso negado ao projeto '{repository_name}'. Verifique as permissões do token.")
            else:
                raise ValueError(f"Erro ao acessar projeto '{repository_name}': {e}")
        except gitlab.exceptions.GitlabAuthenticationError as e:
            print(f"[GitLab Provider] Erro de autenticação: {e}")
            raise ValueError(f"Token de autenticação inválido para acessar '{repository_name}'.")
        except ValueError as e:
            print(f"[GitLab Provider] Erro de validação: {e}")
            raise
        except Exception as e:
            print(f"[GitLab Provider] Erro inesperado: {type(e).__name__}: {e}")
            raise ValueError(f"Erro inesperado ao acessar projeto '{repository_name}': {e}") from e
    
    def create_repository(self, repository_name: str, token: str, description: str = "", private: bool = True) -> Project:
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