from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class JobStoreInterface(ABC):
    @abstractmethod
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def set_job(self, job_id: str, job_data: Dict[str, Any]) -> None:
        pass