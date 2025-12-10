from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class JobStoreInterface(ABC):
    """
    Interface para armazenamento de jobs.
    
    Esta interface define o contrato para sistemas de armazenamento de jobs,
    permitindo diferentes implementações (Redis, banco de dados, etc.).
    """
    
    @abstractmethod
    def set_job(self, job_id: str, job_data: Dict[str, Any], ttl: int = 86400):
        """
        Armazena os dados de um job com um TTL (Time To Live) especificado.
        
        Args:
            job_id (str): Identificador único do job
            job_data (Dict[str, Any]): Dados do job a serem armazenados, incluindo
                status, dados de entrada, resultados e metadados
            ttl (int, optional): Tempo de vida em segundos. Padrão é 86400 (24 horas)
        
        Raises:
            ConnectionError: Se não conseguir conectar ao sistema de armazenamento
            ValueError: Se job_id for inválido ou job_data não for serializável
        """
        pass

    @abstractmethod
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera os dados de um job pelo seu identificador.
        
        Args:
            job_id (str): Identificador único do job a ser recuperado
        
        Returns:
            Optional[Dict[str, Any]]: Dados do job se encontrado, None caso contrário.
                O dicionário retornado contém:
                - status: Estado atual do job
                - data: Dados de entrada e resultados
                - error_details: Detalhes de erro, se houver
        
        Raises:
            ConnectionError: Se não conseguir conectar ao sistema de armazenamento
            ValueError: Se job_id for inválido
        """
        pass