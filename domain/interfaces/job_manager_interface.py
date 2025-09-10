from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class IJobManager(ABC):
    @abstractmethod
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def update_job(self, job_id: str, job_data: Dict[str, Any]) -> None:
        pass
    
    @abstractmethod
    def update_job_status(self, job_id: str, status: str) -> None:
        pass
    
    @abstractmethod
    def handle_job_error(self, job_id: str, error: Exception, step: str) -> None:
        pass