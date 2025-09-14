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
    
    def _find_namespace_id(self, gl, namespace: str) -> int:
        print(f"[GitLab Provider] Buscando namespace '{namespace}'...")
        
        # 1. Tenta encontrar como grupo
        try:
            print(f"[GitLab Provider] Tentando encontrar '{namespace}' como grupo...")
            group = gl.groups.get(namespace)
            print(f"[GitLab Provider] Namespace é um grupo. ID: {group.id}")
            return group.id
        except gitlab.exceptions.GitlabGetError:
            print(f"[GitLab Provider] '{namespace}' não é um grupo.")
        
        # 2. Tenta encontrar como usuário
        try:
            print(f"[GitLab Provider] Tentando encontrar '{namespace}' como usuário...")
            users = gl.users.list(username=namespace)
            if users:
                user = users[0]
                print(f"[GitLab Provider] Namespace é um usuário. ID: {user.id}")
                return user.id
            else:
                print(f"[GitLab Provider] Usuário '{namespace}' não encontrado.")
        except Exception as e:
            print(f"[GitLab Provider] Erro ao buscar usuário '{namespace}': {e}")
        
        # 3. Verifica se é o usuário autenticado
        try:
            user = gl.user
            if user.username == namespace:
                print(f"[GitLab Provider] Namespace corresponde ao usuário autenticado. ID: {user.id}")
                return user.id
        except Exception as e:
            print(f"[GitLab Provider] Erro ao verificar usuário autenticado: {e}")
        
        raise ValueError(f"Namespace '{namespace}' não foi encontrado como grupo nem como usuário. Verifique se o namespace existe e se o token tem acesso a ele.")
    
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
    
        # Estratégia de fallback: tenta buscar por formato original e depois pelo alternativo
        project = None
        last_error = None
        
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
                
        except gitlab.exceptions.GitlabGetError as e:
            last_error = e
            print(f"[GitLab Provider] Primeira tentativa falhou: {e}")
            
            # Fallback: se falhou com nome completo, tenta interpretar como ID se for numérico
            if not self._is_project_id(normalized_identifier):
                # Tenta extrair um possível ID do final do path
                parts = normalized_identifier.split('/')
                if len(parts) >= 2 and parts[-1].isdigit():
                    try:
                        fallback_id = int(parts[-1])
                        print(f"[GitLab Provider] Tentando fallback com possível ID: {fallback_id}")
                        project = gl.projects.get(fallback_id)
                        print(f"[GitLab Provider] Projeto encontrado via fallback ID: '{project.name_with_namespace}' (ID: {project.id}).")
                        last_error = None
                    except Exception as fallback_e:
                        print(f"[GitLab Provider] Fallback também falhou: {fallback_e}")
        
        except Exception as e:
            last_error = e
            print(f"[GitLab Provider] Erro inesperado na busca: {e}")
        
        # Se ainda não encontrou o projeto, processa o erro
        if project is None and last_error:
            if isinstance(last_error, gitlab.exceptions.GitlabGetError):
                if last_error.response_code == 404:
                    if self._is_project_id(normalized_identifier):
                        print(f"[GitLab Provider] ERRO: Projeto com ID '{normalized_identifier}' não encontrado (404).")
                        raise ValueError(f"Projeto GitLab com ID '{normalized_identifier}' não encontrado. Verifique se o ID está correto e se o token tem acesso a ele.")
                    else:
                        print(f"[GitLab Provider] ERRO: Projeto '{normalized_identifier}' não encontrado (404).")
                        raise ValueError(f"Repositório GitLab '{normalized_identifier}' não encontrado. Verifique se o namespace/projeto existe e se o token tem acesso a ele. Formato esperado: 'namespace/projeto' ou Project ID numérico.")
                elif last_error.response_code == 403:
                    print(f"[GitLab Provider] ERRO: Acesso negado ao projeto '{normalized_identifier}' (403).")
                    raise ValueError(f"Acesso negado ao repositório '{normalized_identifier}'. Verifique as permissões do token.")
                else:
                    raise RuntimeError(f"Erro da API do GitLab ao buscar repositório ({last_error.response_code}): {last_error}")
            else:
                raise RuntimeError(f"Erro inesperado ao buscar o projeto GitLab '{normalized_identifier}': {last_error}") from last_error
        
        if project is None:
            raise RuntimeError(f"Falha inexplicável ao buscar projeto '{normalized_identifier}'")
            
        if not hasattr(project, 'default_branch'):
            default_branch = project.attributes.get('default_branch', 'main')
            project.default_branch = default_branch
            print(f"[GitLab Provider] Branch padrão definida: {default_branch}")
        
        return project
        
    def create_repository(self, repository_name: str, token: str = None, description: str = "", private: bool = True) -> Project:
        """Cria um novo repositório GitLab, tratando namespaces de usuário e de grupo."""
        normalized_identifier = str(repository_name).strip()
        print(f"[GitLab Provider] Tentando criar repositório: {normalized_identifier}")
        
        try:
            namespace, project_name = self._parse_repository_name(normalized_identifier)
        except ValueError as e:
            raise ValueError(f"Nome de repositório inválido para criação: '{normalized_identifier}'. Use 'namespace/projeto'.") from e
    
        try:
            # Pega as informações do usuário autenticado pelo token
            user = self.client.user
            print(f"[GitLab Provider] Usuário autenticado: {user.username}")
            
            project_data = {
                'name': project_name,
                'path': project_name,
                'description': description or "Projeto criado automaticamente.",
                'visibility': 'private' if private else 'public',
                'initialize_with_readme': True
            }
    
            # --- LÓGICA CORRIGIDA E DEFINITIVA ---
            # Compara o namespace desejado (em minúsculas) com o username do usuário (em minúsculas)
            if user.username.lower() != namespace.lower():
                # Se o namespace NÃO for o do usuário, busca o ID do GRUPO
                print(f"[GitLab Provider] Namespace '{namespace}' é um grupo. Buscando ID do grupo...")
                try:
                    group = self.client.groups.get(namespace)
                    project_data['namespace_id'] = group.id
                    print(f"[GitLab Provider] ID do grupo '{namespace}' encontrado: {group.id}")
                except gitlab.exceptions.GitlabGetError:
                     raise ValueError(f"O namespace '{namespace}' não foi encontrado como um grupo, e não é o seu namespace pessoal ({user.username}).")
            else:
                # Se o namespace é o do usuário, NÃO enviamos o namespace_id.
                # A API do GitLab usará o usuário autenticado como padrão para criar no namespace pessoal.
                print(f"[GitLab Provider] Criando projeto no namespace pessoal de '{user.username}'.")
    
            # Cria o projeto com os dados corretos
            project = self.client.projects.create(project_data)
            print(f"[GitLab Provider] Projeto criado com sucesso: {project.web_url}")
            return project
            
        except gitlab.exceptions.GitlabCreateError as e:
            if "has already been taken" in str(e):
                raise ValueError(f"Projeto '{normalized_identifier}' já existe.") from e
            raise ConnectionError(f"Erro ao criar projeto '{normalized_identifier}': {e}") from e
        except Exception as e:
            raise RuntimeError(f"Erro inesperado ao criar projeto '{normalized_identifier}': {e}") from e
