from typing import Optional
from repositories.analysis_name_repository import AnalysisNameRepository

class AnalysisNameService:
    def __init__(self, repository: AnalysisNameRepository):
        self.repository = repository
    
    def create_mapping(self, analysis_name: str, job_id: str) -> None:
        self.repository.set_mapping(analysis_name, job_id)
    
    def find_job_id_by_analysis_name(self, analysis_name: str) -> Optional[str]:
        return self.repository.get_job_id(analysis_name)