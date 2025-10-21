from typing import Optional
from domain.interfaces.job_store_interface import JobStoreInterface

class AnalysisNameService:
    def __init__(self, cache: 'AnalysisNameCache'):
        self.cache = cache
    
    def register_analysis(self, analysis_name: str, job_id: str) -> None:
        self.cache.set_mapping(analysis_name, job_id)
    
    def find_job_by_analysis_name(self, analysis_name: str) -> Optional[str]:
        return self.cache.get_job_id(analysis_name)

class AnalysisNameCache:
    def __init__(self, job_store: JobStoreInterface):
        self.job_store = job_store
        self.cache_key = "analysis_name_to_job_id"
    
    def set_mapping(self, analysis_name: str, job_id: str) -> None:
        try:
            current_mapping = self.job_store.redis_client.hgetall(self.cache_key)
            current_mapping[analysis_name] = job_id
            self.job_store.redis_client.hset(self.cache_key, analysis_name, job_id)
        except Exception as e:
            print(f"Erro ao persistir mapeamento de análise: {e}")
    
    def get_job_id(self, analysis_name: str) -> Optional[str]:
        try:
            job_id = self.job_store.redis_client.hget(self.cache_key, analysis_name)
            return job_id.decode('utf-8') if job_id else None
        except Exception as e:
            print(f"Erro ao buscar mapeamento de análise: {e}")
            return None