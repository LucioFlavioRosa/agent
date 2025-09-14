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
            
            # Busca o namespace_id usando a nova lógica robusta
            try:
                namespace_id = self._find_namespace_id(gl, namespace)
                project_data['namespace_id'] = namespace_id
            except ValueError as ns_error:
                print(f"[GitLab Provider] Erro ao encontrar namespace: {ns_error}")
                raise ValueError(f"Não foi possível criar o projeto '{normalized_identifier}': {ns_error}")
            
            project = gl.projects.create(project_data)
            
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