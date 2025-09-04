# Arquivo: AzureReader (VERSÃO CORRIGIDA E OTIMIZADA)

import requests
from typing import Dict, Optional, List
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_repository_provider import AzureRepositoryProvider
from tools.conectores.azure_conector import AzureConector
import base64

class AzureReader:
    
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None):
        # A injeção de dependência aqui é ótima, mas o resto do código não a usa.
        # Vamos manter por consistência, mas o `_get_azure_auth_headers` cria seu próprio conector.
        self.repository_provider = repository_provider or AzureRepositoryProvider()

    def _get_azure_auth_headers(self, repositorio_dict: dict) -> dict:
        # Esta função está correta e não precisa de mudanças.
        connector = AzureConector.create_with_defaults()
        organization = repositorio_dict.get('_organization')
        token = connector._get_token_for_org(organization)
        
        credentials = base64.b64encode(f":{token}".encode()).decode()
        return {
            "Content-Type": "application/json",
            "Authorization": f"Basic {credentials}"
        }

    # ### FUNÇÃO REMOVIDA ###
    # A função _ler_arquivos_especificos é redundante. Podemos usar a _ler_repositorio_completo
    # para ambos os casos, apenas mudando como filtramos a lista de arquivos.

    def _ler_repositorio_completo(self, repositorio_dict: dict, branch_a_ler: str, extensoes_alvo: List[str], arquivos_especificos: Optional[List[str]] = None) -> Dict[str, str]:
        arquivos_do_repo = {}
        
        organization = repositorio_dict.get('_organization')
        project = repositorio_dict.get('_project')
        repository = repositorio_dict.get('_repository')
        
        print(f"[Azure Reader] Lendo repo: {organization}/{project}/{repository}")
        
        headers = self._get_azure_auth_headers(repositorio_dict)
        base_url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repository}"
        
        try:
            print(f"[Azure Reader] Obtendo árvore de arquivos da branch '{branch_a_ler}'...")
            
            # Chamada ÚNICA para buscar a lista de todos os arquivos
            items_url = f"{base_url}/items?recursionLevel=Full&versionDescriptor.version={branch_a_ler}&api-version=7.0"
            response = requests.get(items_url, headers=headers, timeout=60) # Aumentado o timeout
            response.raise_for_status() # Lança erro para status 4xx/5xx
            
            all_items = response.json().get('value', [])
            print(f"[Azure Reader] Árvore obtida. {len(all_items)} itens totais encontrados.")

            # Filtra os itens para pegar apenas os arquivos que queremos
            if arquivos_especificos:
                print(f"[Azure Reader] Filtrando por {len(arquivos_especificos)} arquivos específicos.")
                arquivos_para_ler = [
                    item for item in all_items
                    if not item.get('isFolder') and item.get('path') in arquivos_especificos
                ]
            else:
                print(f"[Azure Reader] Filtrando por extensões: {extensoes_alvo}")
                arquivos_para_ler = [
                    item for item in all_items
                    if not item.get('isFolder') and any(item.get('path', '').endswith(ext) for ext in extensoes_alvo)
                ]

            print(f"[Azure Reader] {len(arquivos_para_ler)} arquivos selecionados para leitura de conteúdo.")

            # ### OTIMIZAÇÃO PRINCIPAL ###
            # Agora, fazemos UMA chamada para cada arquivo para buscar seu conteúdo.
            # Infelizmente, a API do Azure não tem um "bulk get content", mas isso isola o problema.
            for item in arquivos_para_ler:
                file_path = item.get('path')
                try:
                    # A URL para o conteúdo já vem no item! Não precisamos construir uma nova.
                    content_url = item.get('url')
                    if not content_url:
                        continue # Pula se não houver URL
                    
                    # Para obter o conteúdo como texto, adicione o header 'Accept'
                    content_headers = headers.copy()
                    content_headers['Accept'] = 'application/octet-stream' # Pede o conteúdo bruto
                    
                    content_response = requests.get(content_url, headers=content_headers, timeout=30)
                    content_response.raise_for_status()
                    
                    # O conteúdo virá diretamente no corpo da resposta
                    arquivos_do_repo[file_path] = content_response.text
                    print(f"[Azure Reader] Conteúdo de '{file_path}' lido com sucesso.")

                except Exception as e:
                    print(f"[Azure Reader] AVISO: Falha ao ler conteúdo de '{file_path}'. Erro: {e}")

        except Exception as e:
            print(f"[Azure Reader] ERRO CRÍTICO ao ler repositório Azure DevOps: {e}")
            raise
        
        return arquivos_do_repo

    # ### FUNÇÃO PRINCIPAL MODIFICADA ###
    # Agora ela chama a função otimizada para ambos os casos.
    def read_repository_internal(
        self, 
        repositorio, 
        tipo_analise: str, 
        nome_branch: str = None,
        arquivos_especificos: Optional[List[str]] = None,
        mapeamento_tipo_extensoes: Dict = None
    ) -> Dict[str, str]:
        
        branch_a_ler = nome_branch or repositorio.get('default_branch', 'main')
        
        extensoes_alvo = []
        if not arquivos_especificos:
            extensoes_alvo = mapeamento_tipo_extensoes.get(tipo_analise.lower())
            if extensoes_alvo is None:
                raise ValueError(f"Tipo de análise '{tipo_analise}' não encontrado no mapeamento")
        
        # Chama a ÚNICA função de leitura, passando os filtros corretos
        return self._ler_repositorio_completo(
            repositorio_dict=repositorio,
            branch_a_ler=branch_a_ler,
            extensoes_alvo=extensoes_alvo,
            arquivos_especificos=arquivos_especificos
        )
