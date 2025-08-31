from abc import ABC, abstractmethod
from typing import Dict, Optional, List

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
        nome_branch: str = None,
        arquivos_especificos: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Lê os arquivos do repositório e retorna um dicionário {caminho: conteudo}.
        
        Args:
            nome_repo (str): Nome do repositório no formato 'org/repo'
            tipo_analise (str): Tipo de análise que determina extensões relevantes
            nome_branch (str, optional): Nome da branch. Se None, usa branch padrão
            arquivos_especificos (Optional[List[str]], optional): Lista de caminhos
                específicos de arquivos para ler. Se fornecido, ignora filtro por
                extensão e lê apenas os arquivos listados. Defaults to None
        
        Returns:
            Dict[str, str]: Dicionário mapeando caminhos de arquivo para conteúdo
        
        Note:
            - Quando arquivos_especificos é fornecido, o filtro por extensão é ignorado
            - Arquivos não encontrados são tratados com warning, não erro fatal
            - Modo padrão (arquivos_especificos=None) mantém comportamento original
        """
        pass