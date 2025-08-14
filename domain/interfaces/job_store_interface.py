from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class JobStoreInterface(ABC):
    """
    Interface para armazenamento de jobs.
    """
    @abstractmethod
    def set_job(self, job_id: str, job_data: Dict[str, Any], ttl: int = 86400):
        pass

    @abstractmethod
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        pass
