from typing import Dict, Union
from domain.interfaces.secret_manager_interface import ISecretManager
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.gitlab_repository_provider import GitLabRepositoryProvider
from tools.conectores.base_conector import BaseConector

class GitLabConector(BaseConector):
    
    def _is_gitlab_project_id(self, repositorio: str) -> bool:
        try:
            int(repositorio)
            return True
        except ValueError:
            return False
    
    def _extract_org_name(self, repositorio: str) -> str:
        if self._is_gitlab_project_id(repositorio):
            print(f"[GitLab Conector] GitLab Project ID detectado: {repositorio}. Usando 'gitlab' como org_name para busca de token.")
            return 'gitlab'
        else:
            print(f"[GitLab Conector] GitLab path detectado: {repositorio}. Extraindo namespace para busca de token.")
            try:
                parts = repositorio.strip().split('/')
                if len(parts) >= 2:
                    namespace = parts[0]
                    print(f"[GitLab Conector] Namespace GitLab extraído: {namespace}")
                    return namespace
                else:
                    print(f"[GitLab Conector] Path GitLab inválido. Usando 'gitlab' como fallback.")
                    return 'gitlab'
            except (ValueError, IndexError):
                print(f"[GitLab Conector] Erro ao extrair namespace do path GitLab. Usando 'gitlab' como fallback.")
                return 'gitlab'
    
    def _normalize_repository_identifier(self, repositorio: str) -> str:
        if self._is_gitlab_project_id(repositorio):
            normalized = str(repositorio).strip()
            print(f"[GitLab Conector] GitLab Project ID normalizado: {normalized}")
            return normalized
        else:
            normalized = repositorio.strip()
            print(f"[GitLab Conector] GitLab path normalizado: {normalized}")
            return normalized
    
    def _check_namespace_exists(self, gitlab_client, namespace: str) -> Dict[str, Union[str, bool]]:
        try:
            try:
                user = gitlab_client.users.list(username=namespace)
                if user:
                    print(f"[GitLab Conector] Namespace '{namespace}' encontrado como usuário.")
                    return {'exists': True, 'type': 'user', 'id': user[0].id}
            except Exception:
                pass
            
            try:
                group = gitlab_client.groups.get(namespace)
                if group:
                    print(f"[GitLab Conector] Namespace '{namespace}' encontrado como grupo.")
                    return {'exists': True, 'type': 'group', 'id': group.id}
            except Exception:
                pass
            
            print(f"[GitLab Conector] Namespace '{namespace}' não encontrado como usuário nem grupo.")
            return {'exists': False, 'type': None, 'id': None}
            
        except Exception as e:
            print(f"[GitLab Conector] Erro ao verificar namespace '{namespace}': {e}")
            return {'exists': False, 'type': None, 'id': None}
    
    def _create_project_by_path(self, gitlab_client, repositorio_path: str) -> object:
        parts = repositorio_path.split('/')
        if len(parts) < 2:
            raise ValueError(f"Formato de repositório inválido: '{repositorio_path}'. Use 'namespace/projeto'.")
        
        namespace = parts[0]
        project_name = parts[1]
        
        print(f"[GitLab Conector] Tentando criar projeto '{project_name}' no namespace '{namespace}'...")
        
        namespace_info = self._check_namespace_exists(gitlab_client, namespace)
        
        if not namespace_info['exists']:
            raise ValueError(
                f"O namespace '{namespace}' não foi encontrado como um grupo nem como usuário no GitLab. "
                f"Verifique se: (1) o namespace existe, (2) você tem permissão para acessá-lo, "
                f"(3) o token tem os escopos necessários (api, read_user, read_repository)."
            )
        
        try:
            project_data = {
                'name': project_name,
                'path': project_name,
                'visibility': 'private'
            }
            
            if namespace_info['type'] == 'group':
                project_data['namespace_id'] = namespace_info['id']
                print(f"[GitLab Conector] Criando projeto no grupo '{namespace}' (ID: {namespace_info['id']})...")
            else:
                current_user = gitlab_client.user
                if current_user.username != namespace:
                    raise ValueError(
                        f"Não é possível criar projeto no namespace de usuário '{namespace}'. "
                        f"O token pertence ao usuário '{current_user.username}'. "
                        f"Para criar em outro usuário, use um grupo ou ajuste as permissões."
                    )
                print(f"[GitLab Conector] Criando projeto no namespace do usuário atual '{namespace}'...")
            
            created_project = gitlab_client.projects.create(project_data)
            print(f"[GitLab Conector] Projeto '{repositorio_path}' criado com sucesso! ID: {created_project.id}")
            return created_project
            
        except Exception as create_error:
            if "already exists" in str(create_error).lower():
                print(f"[GitLab Conector] Projeto '{repositorio_path}' já existe. Tentando acessá-lo...")
                try:
                    return gitlab_client.projects.get(repositorio_path)
                except Exception as get_error:
                    raise ValueError(
                        f"Projeto '{repositorio_path}' existe mas não pode ser acessado. "
                        f"Verifique as permissões do token. Erro: {get_error}"
                    ) from get_error
            else:
                raise ValueError(
                    f"Erro inesperado ao criar projeto '{repositorio_path}': {create_error}"
                ) from create_error
    
    def _get_project_by_id(self, gitlab_client, project_id: str) -> object:
        try:
            print(f"[GitLab Conector] Buscando projeto por ID: {project_id}")
            project = gitlab_client.projects.get(project_id)
            print(f"[GitLab Conector] Projeto encontrado: {project.path_with_namespace} (ID: {project.id})")
            return project
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                raise ValueError(
                    f"Projeto GitLab com ID '{project_id}' não encontrado. "
                    f"Verifique se: (1) o ID está correto, (2) o projeto existe, "
                    f"(3) você tem permissão para acessá-lo."
                ) from e
            else:
                raise ValueError(
                    f"Erro inesperado ao acessar projeto ID '{project_id}': {e}"
                ) from e
    
    def _get_project_by_path(self, gitlab_client, repositorio_path: str) -> object:
        try:
            print(f"[GitLab Conector] Buscando projeto por caminho: {repositorio_path}")
            project = gitlab_client.projects.get(repositorio_path)
            print(f"[GitLab Conector] Projeto encontrado: {project.path_with_namespace} (ID: {project.id})")
            return project
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                print(f"[GitLab Conector] Projeto '{repositorio_path}' não encontrado. Tentando criar...")
                return self._create_project_by_path(gitlab_client, repositorio_path)
            else:
                raise ValueError(
                    f"Erro inesperado ao acessar projeto '{repositorio_path}': {e}"
                ) from e
    
    def connection(self, repositorio: str) -> Union[object]:
        normalized_repo = self._normalize_repository_identifier(repositorio)
        org_name = self._extract_org_name(normalized_repo)
        
        try:
            gitlab_client = self._handle_repository_connection(normalized_repo, "GitLab", org_name)
            
            if self._is_gitlab_project_id(normalized_repo):
                return self._get_project_by_id(gitlab_client, normalized_repo)
            else:
                return self._get_project_by_path(gitlab_client, normalized_repo)
                
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(
                f"Erro fatal ao conectar com repositório GitLab '{normalized_repo}': {e}"
            ) from e
    
    @classmethod
    def create_with_defaults(cls) -> 'GitLabConector':
        return cls(repository_provider=GitLabRepositoryProvider())
