from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class IReportManager(ABC):
    @abstractmethod
    def try_read_existing_report(self, job_id: str, job_info: Dict[str, Any], current_step_index: int) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def save_report_to_blob(self, job_id: str, job_info: Dict[str, Any], report_text: str, report_generated_by_agent: bool) -> None:
        pass
    
    @abstractmethod
    def handle_report_only_mode(self, job_id: str, job_info: Dict[str, Any], step_result: Dict[str, Any]) -> None:
        pass