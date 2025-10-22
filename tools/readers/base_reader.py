from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Callable

class BaseReader(ABC):
    
    def __init__(self, repository_provider):
        self.repository_provider = repository_provider

    def _validar_parametros_leitura(self, repositorio, nome_branch: Optional[str], provider_name: str) -> str:
        if nome_branch:
            print(f"Branch especificada pelo usuário: '{nome_branch}'")
            return nome_branch
        
        if hasattr(repositorio, 'default_branch'):
            branch_padrao = repositorio.default_branch
        elif isinstance(repositorio, dict) and 'default_branch' in repositorio:
            branch_padrao = repositorio['default_branch']
        else:
            branch_padrao = 'main'
            print(f"AVISO: Branch padrão não encontrada no repositório {provider_name}. Usando 'main' como fallback.")
        
        print(f"Usando branch padrão do repositório {provider_name}: '{branch_padrao}'")
        return branch_padrao

    def _validar_extensoes_alvo(self, tipo_analise: str, mapeamento_tipo_extensoes: Dict) -> List[str]:
        extensoes_alvo = mapeamento_tipo_extensoes.get(tipo_analise.lower())
        if extensoes_alvo is None:
            raise ValueError(
                f"Tipo de análise '{tipo_analise}' não encontrado no mapeamento de extensões. "
                f"Tipos válidos: {list(mapeamento_tipo_extensoes.keys())}"
            )
        return extensoes_alvo

    def _ler_arquivos_especificos_base(
        self, 
        repositorio, 
        branch_a_ler: str, 
        arquivos_especificos: List[str],
        provider_name: str,
        read_file_func: Callable
    ) -> Dict[str, str]:
        arquivos_lidos = {}
        print(f"Iniciando leitura de {len(arquivos_especificos)} arquivos específicos do repositório {provider_name}...")
        
        for i, caminho_arquivo in enumerate(arquivos_especificos):
            if (i + 1) % 10 == 0:
                print(f"  ...lendo arquivo {i + 1} de {len(arquivos_especificos)} ({caminho_arquivo})")
            
            try:
                conteudo = read_file_func(repositorio, caminho_arquivo, branch_a_ler)
                arquivos_lidos[caminho_arquivo] = conteudo
            except FileNotFoundError:
                print(f"AVISO: Arquivo '{caminho_arquivo}' não encontrado na branch '{branch_a_ler}'. Pulando.")
            except PermissionError:
                print(f"AVISO: Sem permissão para ler o arquivo '{caminho_arquivo}'. Pulando.")
            except Exception as e:
                print(f"AVISO: Falha ao ler o arquivo '{caminho_arquivo}'. Erro: {e}. Pulando.")
        
        print(f"Leitura de arquivos específicos {provider_name} concluída. {len(arquivos_lidos)} de {len(arquivos_especificos)} arquivos lidos com sucesso.")
        return arquivos_lidos

    @abstractmethod
    def _obter_lista_todos_arquivos(self, repositorio, branch_a_ler: str) -> List[str]:
        pass

    @abstractmethod
    def read_repository_internal(
        self, 
        repositorio, 
        tipo_analise: str, 
        nome_branch: str,
        arquivos_especificos: Optional[List[str]],
        mapeamento_tipo_extensoes: Dict,
        retornar_lista_arquivos: bool
    ) -> Dict:
        pass