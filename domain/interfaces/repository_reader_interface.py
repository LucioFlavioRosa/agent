from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Union

class IRepositoryReader(ABC):
    """
    Interface para leitores de repositório de código-fonte.
    
    Esta interface define o contrato para leitura de repositórios,
    suportando tanto leitura completa quanto leitura filtrada por
    lista específica de arquivos.
    """
    @abstractmethod
    def read_repository(
        self, 
        nome_repo: str, 
        tipo_analise: str,
        repository_type: str,
        nome_branch: str = None,
        arquivos_especificos: Optional[List[str]] = None,
        retornar_lista_arquivos: bool = False
    ) -> Union[Dict[str, str], Dict[str, Union[Dict[str, str], List[str]]]]:
        """
        Lê os arquivos do repositório e retorna um dicionário {caminho: conteudo}.
        
        Args:
            nome_repo (str): Nome do repositório no formato 'org/repo'
            tipo_analise (str): Tipo de análise que determina extensões relevantes
            repository_type (str): Tipo do repositório ('github', 'gitlab', 'azure')
            nome_branch (str, optional): Nome da branch. Se None, usa branch padrão
            arquivos_especificos (Optional[List[str]], optional): Lista de caminhos
                específicos de arquivos para ler. Se fornecido, ignora filtro por
                extensão e lê apenas os arquivos listados. Defaults to None
            retornar_lista_arquivos (bool, optional): Se True, retorna também lista
                de todos os arquivos do repositório. Defaults to False
        
        Returns:
            Union[Dict[str, str], Dict[str, Union[Dict[str, str], List[str]]]]: 
                Se retornar_lista_arquivos=False: Dicionário mapeando caminhos para conteúdo
                Se retornar_lista_arquivos=True: {'codigo': Dict[caminho, conteudo], 'lista_arquivos': List[str]}
        
        Note:
            - Quando arquivos_especificos é fornecido, o filtro por extensão é ignorado
            - Arquivos não encontrados são tratados com warning, não erro fatal
            - Modo padrão (arquivos_especificos=None) mantém comportamento original
            - retornar_lista_arquivos permite obter lista completa de arquivos do repositório
        """
        pass