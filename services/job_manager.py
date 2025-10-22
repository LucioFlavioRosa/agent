import traceback
from typing import Dict, Any, Optional
from domain.interfaces.job_manager_interface import IJobManager
from tools.job_store import RedisJobStore

class JobManager(IJobManager):
    def __init__(self, job_store: RedisJobStore):
        self.job_store = job_store
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.job_store.get_job(job_id)
    
    def update_job(self, job_id: str, job_data: Dict[str, Any]) -> None:
        self.job_store.set_job(job_id, job_data)
    
    def update_job_status(self, job_id: str, status: str) -> None:
        job_info = self.get_job(job_id)
        if job_info:
            job_info['status'] = status
            self.update_job(job_id, job_info)
    
    def handle_job_error(self, job_id: str, error: Exception, step: str) -> None:
        error_message = f"Erro fatal durante a etapa '{step}': {str(error)}"
        print(f"[{job_id}] {error_message}")
        traceback.print_exc()
        
        try:
            job_info = self.get_job(job_id)
            if job_info:
                job_info['status'] = 'failed'
                job_info['error_details'] = error_message
                self.update_job(job_id, job_info)
        except Exception as redis_e:
            print(f"[{job_id}] ERRO CRÍTICO ADICIONAL: Falha ao registrar o erro no Redis. Erro: {redis_e}")