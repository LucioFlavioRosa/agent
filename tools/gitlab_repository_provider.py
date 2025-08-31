import gitlab
from gitlab.v4.objects import Project
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from typing import Any

class GitLabRepositoryProvider(IRepositoryProvider):
    
    def get_repository(self, repository_name: str, token: str) -> Project:
        try:
            gl = gitlab.Gitlab(url="https://gitlab.com", private_token=token)
            project = gl.projects.get(repository_name, lazy=True)
            _ = project.name
            
            # Adiciona métodos de compatibilidade para funcionar com o reader
            if not hasattr(project, 'default_branch'):
                try:
                    project.default_branch = project.default_branch or 'main'
                except:
                    project.default_branch = 'main'
            
            return project
            
        except gitlab.exceptions.GitlabGetError as e:
            if e.response_code == 404:
                raise ValueError(f"Projeto '{repository_name}' não encontrado no GitLab.")
            elif e.response_code == 403:
                raise ValueError(f"Acesso negado ao projeto '{repository_name}'. Verifique as permissões do token.")
            else:
                raise ValueError(f"Erro ao acessar projeto '{repository_name}': {e}")
        except gitlab.exceptions.GitlabAuthenticationError:
            raise ValueError(f"Token de autenticação inválido para acessar '{repository_name}'.")
        except Exception as e:
            raise ValueError(f"Erro inesperado ao acessar projeto '{repository_name}': {e}") from e
    
    def create_repository(self, repository_name: str, token: str, description: str = "", private: bool = True) -> Project:
        try:
            namespace_name, project_name_only = repository_name.split('/')
        except ValueError:
            raise ValueError(f"Nome do repositório '{repository_name}' tem formato inválido. Esperado 'namespace/projeto'.")
        
        try:
            gl = gitlab.Gitlab(url="https://gitlab.com", private_token=token)
            
            project_data = {
                'name': project_name_only,
                'path': project_name_only,
                'description': description or "Projeto criado automaticamente pela plataforma de agentes de IA.",
                'visibility': 'private' if private else 'public',
                'initialize_with_readme': True,
                'default_branch': 'main'
            }
            
            try:
                group = gl.groups.get(namespace_name, lazy=True)
                project_data['namespace_id'] = group.id
                project = gl.projects.create(project_data)
                
            except gitlab.exceptions.GitlabGetError:
                if 'namespace_id' in project_data:
                    del project_data['namespace_id']
                project = gl.projects.create(project_data)
            
            # Adiciona métodos de compatibilidade
            if not hasattr(project, 'default_branch'):
                project.default_branch = 'main'
            
            return project
            
        except gitlab.exceptions.GitlabCreateError as e:
            if "has already been taken" in str(e):
                raise ValueError(f"Projeto '{repository_name}' já existe no GitLab.")
            else:
                raise ValueError(f"Erro ao criar projeto '{repository_name}': {e}")
        except gitlab.exceptions.GitlabAuthenticationError:
            raise ValueError(f"Token de autenticação inválido para criar projeto '{repository_name}'.")
        except Exception as e:
            raise ValueError(f"Erro inesperado ao criar projeto '{repository_name}': {e}") from e