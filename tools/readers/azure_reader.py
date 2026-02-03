import requests
from typing import Dict, Optional, List, Union
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_repository_provider import AzureRepositoryProvider
from tools.readers.base_reader import BaseReader
from tools.readers.base_file_reader import BaseFileReader
from tools.user_email_parser import UserEmailParser
import base64

class AzureReader(BaseFileReader):
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None):
        super().__init__(repository_provider or AzureRepositoryProvider())

    def _get_base_api_url(self, repo_name: dict) -> str:
        organization = repo_name.get('_organization')
        project = repo_name.get('_project')
        repository = repo_name.get('_repository')
        return f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repository}"

    def _get_azure_auth_headers(self, repo_name: dict, user_email: Optional[str] = None, group_resolver: Optional['MongoDBGroupResolverService'] = None) -> dict:
        connector = self._get_connector()
        organization = repo_name.get('_organization')
        token = connector._get_token_for_org(self._build_token_key(organization, user_email, group_resolver), platform='azure')
        credentials = base64.b64encode(f":{token}".encode()).decode()
        return {
            "Content-Type": "application/json",
            "Authorization": f"Basic {credentials}"
        }

    def _get_connector(self):
        from tools.conectores.azure_conector import AzureConector
        return AzureConector.create_with_defaults()

    def _build_token_key(self, organization: str, user_email: Optional[str], group_resolver: Optional['MongoDBGroupResolverService'] = None) -> str:
        if user_email:
            usuario, empresa, grupo = UserEmailParser.parse_email_with_group(user_email, group_resolver)
            return f"{grupo}.{empresa}"
        return organization

    def read_single_file(self, repo_name: dict, file_path: str, branch_name: Optional[str] = None, user_email: Optional[str] = None, group_resolver: Optional['MongoDBGroupResolverService'] = None) -> Optional[str]:
        branch_a_ler = branch_name or repo_name.get('default_branch', 'main')
        headers = self._get_azure_auth_headers(repo_name, user_email, group_resolver)
        base_url = self._get_base_api_url(repo_name)
        file_url = f"{base_url}/items?path={file_path}&versionDescriptor.version={branch_a_ler}&$format=text&api-version=7.0"
        try:
            response = requests.get(file_url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception:
            return None

    def _obter_lista_todos_arquivos(self, repo_name: dict, branch_name: str, user_email: Optional[str] = None, group_resolver: Optional['MongoDBGroupResolverService'] = None) -> List[str]:
        headers = self._get_azure_auth_headers(repo_name, user_email, group_resolver)
        base_url = self._get_base_api_url(repo_name)
        try:
            items_url = f"{base_url}/items?recursionLevel=Full&versionDescriptor.version={branch_name}&api-version=7.0"
            response = requests.get(items_url, headers=headers, timeout=60)
            response.raise_for_status()
            all_items = response.json().get('value', [])
            lista_arquivos = [item.get('path') for item in all_items if not item.get('isFolder') and item.get('path')]
            return lista_arquivos
        except Exception:
            return []

    def _ler_repositorio_completo(self, repo_name: dict, branch_name: str, extensoes_alvo: List[str], arquivos_especificos: Optional[List[str]] = None, user_email: Optional[str] = None, group_resolver: Optional['MongoDBGroupResolverService'] = None) -> Dict[str, str]:
        arquivos_do_repo = {}
        headers = self._get_azure_auth_headers(repo_name, user_email, group_resolver)
        base_url = self._get_base_api_url(repo_name)
        try:
            items_url = f"{base_url}/items?recursionLevel=Full&versionDescriptor.version={branch_name}&api-version=7.0"
            response = requests.get(items_url, headers=headers, timeout=60)
            response.raise_for_status()
            all_items = response.json().get('value', [])
            if arquivos_especificos:
                arquivos_para_ler = [item for item in all_items if not item.get('isFolder') and item.get('path') in arquivos_especificos]
            else:
                arquivos_para_ler = [item for item in all_items if not item.get('isFolder') and any(item.get('path', '').endswith(ext) for ext in extensoes_alvo)]
            for item in arquivos_para_ler:
                file_path = item.get('path')
                if file_path:
                    content = self.read_single_file(repo_name, file_path, branch_name, user_email, group_resolver)
                    if content is not None:
                        arquivos_do_repo[file_path] = content
        except Exception:
            pass
        return arquivos_do_repo

    def read_repository_internal(self, repository_type: str, repo_name: dict, branch_name: str = None, analysis_type: str = None, arquivos_especificos: Optional[List[str]] = None, mapeamento_tipo_extensoes: Dict = None, retornar_lista_arquivos: bool = False, user_email: Optional[str] = None, group_resolver: Optional['MongoDBGroupResolverService'] = None) -> Union[Dict[str, str], Dict[str, Union[Dict[str, str], List[str]]]]:
        branch_a_ler = branch_name or repo_name.get('default_branch', 'main')
        extensoes_alvo = []
        if not arquivos_especificos:
            extensoes_alvo = mapeamento_tipo_extensoes.get(analysis_type.lower())
            if extensoes_alvo is None:
                raise ValueError(f"Tipo de análise '{analysis_type}' não encontrado no mapeamento")
        arquivos_lidos = self._ler_repositorio_completo(
            repo_name=repo_name,
            branch_name=branch_a_ler,
            extensoes_alvo=extensoes_alvo,
            arquivos_especificos=arquivos_especificos,
            user_email=user_email,
            group_resolver=group_resolver
        )
        if retornar_lista_arquivos:
            lista_todos_arquivos = self._obter_lista_todos_arquivos(repo_name, branch_a_ler, user_email, group_resolver)
            return {'codigo': arquivos_lidos, 'lista_arquivos': lista_todos_arquivos}
        else:
            return arquivos_lidos
