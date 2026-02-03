import requests
from typing import Dict, Optional, List, Union
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_repository_provider import AzureRepositoryProvider
from tools.conectores.azure_conector import AzureConector
from tools.readers.base_reader import BaseReader
import base64

class AzureReader(BaseReader):
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None):
        super().__init__(repository_provider or AzureRepositoryProvider())

    def _get_base_api_url(self, repo_name: dict) -> str:
        organization = repo_name.get('_organization')
        project = repo_name.get('_project')
        repository = repo_name.get('_repository')
        return f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repository}"

    def _get_azure_auth_headers(self, repo_name: dict) -> dict:
        connector = AzureConector.create_with_defaults()
        organization = repo_name.get('_organization')
        token = connector._get_token_for_org(organization, platform='azure')
        credentials = base64.b64encode(f":{token}".encode()).decode()
        return {
            "Content-Type": "application/json",
            "Authorization": f"Basic {credentials}"
        }

    def read_single_file(self, repo_name: dict, file_path: str, branch_name: Optional[str] = None) -> Optional[str]:
        branch_a_ler = branch_name or repo_name.get('default_branch', 'main')
        print(f"[Azure Reader] Lendo arquivo específico: '{file_path}'")
        headers = self._get_azure_auth_headers(repo_name)
        base_url = self._get_base_api_url(repo_name)
        file_url = f"{base_url}/items?path={file_path}&versionDescriptor.version={branch_a_ler}&$format=text&api-version=7.0"
        try:
            response = requests.get(file_url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            return self._handle_read_error(e, file_path, branch_a_ler, "Azure")

    def _obter_lista_todos_arquivos(self, repo_name: dict, branch_name: str) -> List[str]:
        print(f"[Azure Reader] Obtendo lista completa de arquivos...")
        headers = self._get_azure_auth_headers(repo_name)
        base_url = self._get_base_api_url(repo_name)
        try:
            items_url = f"{base_url}/items?recursionLevel=Full&versionDescriptor.version={branch_name}&api-version=7.0"
            response = requests.get(items_url, headers=headers, timeout=60)
            response.raise_for_status()
            all_items = response.json().get('value', [])
            lista_arquivos = [item.get('path') for item in all_items if not item.get('isFolder') and item.get('path')]
            print(f"[Azure Reader] Lista completa obtida: {len(lista_arquivos)} arquivos encontrados.")
            return lista_arquivos
        except Exception as e:
            print(f"[Azure Reader] ERRO ao obter lista completa de arquivos Azure DevOps: {e}")
            raise

    def _ler_repositorio_completo(self, repo_name: dict, branch_name: str, extensoes_alvo: List[str], arquivos_especificos: Optional[List[str]] = None) -> Dict[str, str]:
        arquivos_do_repo = {}
        headers = self._get_azure_auth_headers(repo_name)
        base_url = self._get_base_api_url(repo_name)
        try:
            print(f"[Azure Reader] Obtendo árvore de arquivos da branch '{branch_name}'...")
            items_url = f"{base_url}/items?recursionLevel=Full&versionDescriptor.version={branch_name}&api-version=7.0"
            response = requests.get(items_url, headers=headers, timeout=60)
            response.raise_for_status()
            all_items = response.json().get('value', [])
            if arquivos_especificos:
                arquivos_para_ler = [item for item in all_items if not item.get('isFolder') and item.get('path') in arquivos_especificos]
            else:
                arquivos_para_ler = [item for item in all_items if not item.get('isFolder') and any(item.get('path', '').endswith(ext) for ext in extensoes_alvo)]
            print(f"[Azure Reader] {len(arquivos_para_ler)} arquivos selecionados para leitura de conteúdo.")
            for item in arquivos_para_ler:
                file_path = item.get('path')
                if file_path:
                    content = self.read_single_file(repo_name, file_path, branch_name)
                    if content is not None:
                        arquivos_do_repo[file_path] = content
        except Exception as e:
            print(f"[Azure Reader] ERRO CRÍTICO ao ler repositório Azure DevOps: {e}")
            raise
        return arquivos_do_repo

    def read_repository_internal(self, repository_type: str, repo_name: dict, branch_name: str = None, analysis_type: str = None, arquivos_especificos: Optional[List[str]] = None, mapeamento_tipo_extensoes: Dict = None, retornar_lista_arquivos: bool = False) -> Union[Dict[str, str], Dict[str, Union[Dict[str, str], List[str]]]]:
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
            arquivos_especificos=arquivos_especificos
        )
        if retornar_lista_arquivos:
            lista_todos_arquivos = self._obter_lista_todos_arquivos(repo_name, branch_a_ler)
            return {'codigo': arquivos_lidos, 'lista_arquivos': lista_todos_arquivos}
        else:
            return arquivos_lidos
