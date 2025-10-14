import requests
import json
from typing import Any, Dict
from domain.interfaces.repository_provider_interface import IRepositoryProvider

class AzureRepositoryProvider(IRepositoryProvider):
    """
    Implementação do provedor de repositório para Azure DevOps.
    Responsabilidade única: interagir com a API REST do Azure DevOps.
    
    Esta classe implementa a interface IRepositoryProvider para Azure DevOps,
    permitindo integração transparente com o sistema existente através
    de injeção de dependências, seguindo o mesmo padrão do GitHub e GitLab.
    
    Características:
    - Suporte a organizações e projetos do Azure DevOps
    - Criação automática de repositórios quando necessário
    - Tratamento robusto de erros da API REST
    - Compatibilidade total com o sistema de conectores existente
    - Utiliza apenas bibliotecas padrão (requests)
    
    Formato do repository_name esperado: 'organization/project/repository'
    
    Example:
        >>> azure_provider = AzureRepositoryProvider()
        >>> connector = GitHubConnector(repository_provider=azure_provider)
        >>> repo = connector.connection("myorg/myproject/myrepo")
    """
    
    def __init__(self):
        """
        Inicializa o provider do Azure DevOps.
        
        Note:
            A URL base da API é construída dinamicamente baseada na organização
            fornecida no repository_name.
        """
        self.api_version = "7.0"
        self.base_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def _parse_repository_name(self, repository_name: str) -> tuple:
        """
        Parseia o nome do repositório no formato Azure DevOps.
        
        Args:
            repository_name (str): Nome no formato 'organization/project/repository'
            
        Returns:
            tuple: (organization, project, repository)
            
        Raises:
            ValueError: Se o formato for inválido
        """
        parts = repository_name.split('/')
        if len(parts) != 3:
            raise ValueError(
                f"Nome do repositório '{repository_name}' tem formato inválido. "
                "Esperado 'organization/project/repository'."
            )
        return parts[0], parts[1], parts[2]
    
    def _get_auth_headers(self, token: str) -> Dict[str, str]:
        """
        Constrói headers de autenticação para Azure DevOps.
        
        Args:
            token (str): Personal Access Token (PAT) do Azure DevOps
            
        Returns:
            Dict[str, str]: Headers com autenticação básica
        """
        import base64
        
        # Azure DevOps usa autenticação básica com PAT
        # Username pode ser qualquer string, password é o PAT
        credentials = base64.b64encode(f":{token}".encode()).decode()
        
        headers = self.base_headers.copy()
        headers["Authorization"] = f"Basic {credentials}"
        return headers
    
    def _build_api_url(self, organization: str, project: str = None, endpoint: str = "") -> str:
        """
        Constrói URL da API do Azure DevOps.
        
        Args:
            organization (str): Nome da organização
            project (str, optional): Nome do projeto
            endpoint (str, optional): Endpoint específico da API
            
        Returns:
            str: URL completa da API
        """
        base_url = f"https://dev.azure.com/{organization}"
        
        if project:
            base_url += f"/{project}"
        
        base_url += "/_apis"
        
        if endpoint:
            base_url += f"/{endpoint}"
        
        base_url += f"?api-version={self.api_version}"
        
        return base_url
    
    def get_repository(self, repository_name: str, token: str) -> Dict[str, Any]:
        """
        Obtém um repositório existente do Azure DevOps.
        
        Args:
            repository_name (str): Nome do repositório no formato 'organization/project/repository'
            token (str): Personal Access Token com permissões de leitura
            
        Returns:
            Dict[str, Any]: Dados do repositório do Azure DevOps
            
        Raises:
            ValueError: Se o repositório não for encontrado ou houver erro de acesso
        
        Note:
            - O token deve ter permissões de leitura no projeto
            - Retorna um dicionário com dados do repositório para compatibilidade
        """
        try:
            organization, project, repo_name = self._parse_repository_name(repository_name)
            
            # Constrói URL para buscar o repositório específico
            url = self._build_api_url(
                organization=organization,
                project=project,
                endpoint=f"git/repositories/{repo_name}"
            )
            
            headers = self._get_auth_headers(token)
            
            print(f"Buscando repositório Azure DevOps: {repository_name}")
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 404:
                raise ValueError(f"Repositório '{repository_name}' não encontrado no Azure DevOps.")
            elif response.status_code == 403:
                raise ValueError(f"Acesso negado ao repositório '{repository_name}'. Verifique as permissões do token.")
            elif response.status_code != 200:
                raise ValueError(f"Erro ao acessar repositório '{repository_name}': {response.status_code} - {response.text}")
            
            repo_data = response.json()
            
            # Adiciona informações úteis para o sistema
            repo_data['_provider_type'] = 'azure_devops'
            repo_data['_full_name'] = repository_name
            repo_data['_organization'] = organization
            repo_data['_project'] = project
            repo_data['_repository'] = repo_name
            repo_data['default_branch'] = repo_data.get('defaultBranch', 'refs/heads/main').replace('refs/heads/', '')
            
            return repo_data
            
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Erro de rede ao acessar repositório '{repository_name}': {e}") from e
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Erro inesperado ao acessar repositório '{repository_name}': {e}") from e
    
    def create_repository(self, repository_name: str, token: str, description: str = "", private: bool = True) -> Dict[str, Any]:
        """
        Cria um novo repositório no Azure DevOps.
        
        Args:
            repository_name (str): Nome do repositório no formato 'organization/project/repository'
            token (str): Personal Access Token com permissões de criação
            description (str, optional): Descrição do repositório. Defaults to ""
            private (bool, optional): Se o repositório deve ser privado (sempre True no Azure DevOps por projeto). Defaults to True
            
        Returns:
            Dict[str, Any]: Dados do repositório criado
            
        Raises:
            ValueError: Se houver erro na criação ou formato inválido do nome
        
        Note:
            - O token deve ter permissões de criação no projeto
            - Repositórios no Azure DevOps herdam a visibilidade do projeto
            - O parâmetro private é mantido para compatibilidade mas não afeta a criação
        """
        try:
            organization, project, repo_name = self._parse_repository_name(repository_name)
            
            # Primeiro verifica se o projeto existe
            project_url = self._build_api_url(
                organization=organization,
                endpoint=f"projects/{project}"
            )
            
            headers = self._get_auth_headers(token)
            
            print(f"Verificando projeto Azure DevOps: {organization}/{project}")
            project_response = requests.get(project_url, headers=headers, timeout=30)
            
            if project_response.status_code == 404:
                raise ValueError(f"Projeto '{project}' não encontrado na organização '{organization}'.")
            elif project_response.status_code != 200:
                raise ValueError(f"Erro ao acessar projeto '{project}': {project_response.status_code} - {project_response.text}")
            
            # Constrói URL para criar o repositório
            url = self._build_api_url(
                organization=organization,
                project=project,
                endpoint="git/repositories"
            )
            
            # Payload para criação do repositório
            payload = {
                "name": repo_name,
                "project": {
                    "id": project_response.json()["id"]
                }
            }
            
            # Adiciona descrição se fornecida
            if description:
                payload["description"] = description
            else:
                payload["description"] = "Repositório criado automaticamente pela plataforma de agentes de IA."
            
            print(f"Criando repositório Azure DevOps: {repository_name}")
            response = requests.post(
                url, 
                headers=headers, 
                data=json.dumps(payload),
                timeout=30
            )
            
            if response.status_code == 409:
                raise ValueError(f"Repositório '{repository_name}' já existe no Azure DevOps.")
            elif response.status_code == 403:
                raise ValueError(f"Permissão negada para criar repositório '{repository_name}'. Verifique as permissões do token.")
            elif response.status_code not in [200, 201]:
                raise ValueError(f"Erro ao criar repositório '{repository_name}': {response.status_code} - {response.text}")
            
            repo_data = response.json()
            
            # Adiciona informações úteis para o sistema
            repo_data['_provider_type'] = 'azure_devops'
            repo_data['_full_name'] = repository_name
            repo_data['_organization'] = organization
            repo_data['_project'] = project
            repo_data['_repository'] = repo_name
            repo_data['default_branch'] = repo_data.get('defaultBranch', 'refs/heads/main').replace('refs/heads/', '')
            
            print(f"Repositório '{repository_name}' criado com sucesso no Azure DevOps.")
            return repo_data
            
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Erro de rede ao criar repositório '{repository_name}': {e}") from e
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Erro inesperado ao criar repositório '{repository_name}': {e}") from e
