from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class JobStoreInterface(ABC):
    """
    Interface para armazenamento de jobs.
    Implementação obrigatória: RedisJobStore em tools/job_store.py.
    """
    @abstractmethod
    def set_job(self, job_id: str, job_data: Dict[str, Any], ttl: int = 86400):
        """
        Salva o job no armazenamento com TTL.
        """
        pass

    @abstractmethod
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera o job pelo ID.
        """
        pass

    @abstractmethod
    def index_analysis_name(self, job_id: str, analysis_name: str):
        """
        Indexa o nome da análise para permitir busca futura por nome.
        """
        pass

    @abstractmethod
    def get_job_id_by_analysis_name(self, analysis_name: str) -> Optional[str]:
        """
        Recupera o job_id associado ao nome da análise.
        """
        pass
