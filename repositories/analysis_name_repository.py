from typing import Optional
from abstractions.job_store_interface import JobStoreInterface

class AnalysisNameRepository:
    def __init__(self, job_store: JobStoreInterface):
        self.job_store = job_store
        self.cache_key = "analysis_name_to_job_id"
    
    def set_mapping(self, analysis_name: str, job_id: str):
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