import time
from typing import Dict, Any, Optional
from domain.interfaces.job_manager_interface import IJobManager

class JobHandler:
    def __init__(self, job_manager: IJobManager):
        self.job_manager = job_manager
    
    def get_job_info(self, job_id: str) -> Dict[str, Any]:
        job_info = self.job_manager.get_job(job_id)
        if not job_info:
            raise ValueError(f"Job {job_id} não encontrado")
        return job_info
    
    def update_job_status(self, job_id: str, status: str) -> None:
        job_info = self.get_job_info(job_id)
        job_info['status'] = status
        job_info['last_status_update'] = time.time()
        self.job_manager.set_job(job_id, job_info)
        print(f"[{job_id}] Status atualizado para: {status}")
    
    def update_job(self, job_id: str, job_info: Dict[str, Any]) -> None:
        job_info['last_status_update'] = time.time()
        self.job_manager.set_job(job_id, job_info)
    
    def get_step_result(self, job_info: Dict[str, Any], start_from_step: int) -> Optional[Dict[str, Any]]:
        if start_from_step > 0:
            step_key = f"step_{start_from_step - 1}_result"
            return job_info['data'].get(step_key)
        return None
    
    def save_step_result(self, job_info: Dict[str, Any], step_index: int, step_result: Dict[str, Any]) -> None:
        step_key = f"step_{step_index}_result"
        job_info['data'][step_key] = step_result
    
    def get_approval_instructions(self, job_info: Dict[str, Any]) -> Optional[str]:
        return job_info['data'].get('instrucoes_extras_aprovacao')
    
    def clear_approval_instructions(self, job_info: Dict[str, Any]) -> None:
        if 'instrucoes_extras_aprovacao' in job_info['data']:
            del job_info['data']['instrucoes_extras_aprovacao']
    
    def set_paused_step(self, job_info: Dict[str, Any], step_index: int) -> None:
        job_info['data']['paused_at_step'] = step_index
    
    def handle_job_error(self, job_id: str, error: Exception, context: str) -> None:
        try:
            job_info = self.get_job_info(job_id)
            job_info['status'] = 'failed'
            job_info['last_status_update'] = time.time()
            job_info['error_details'] = f"Erro em {context}: {str(error)}"
            self.job_manager.set_job(job_id, job_info)
            print(f"[{job_id}] Job marcado como failed devido a erro em {context}: {str(error)}")
        except Exception as e:
            print(f"[{job_id}] ERRO CRÍTICO ao tratar erro do job: {str(e)}")
    
    def abort_job_due_to_timeout(self, job_id: str, job_info: Dict[str, Any]) -> None:
        job_info['status'] = 'failed'
        job_info['last_status_update'] = time.time()
        job_info['error_details'] = "Tempo limite excedido. Considere reduzir o contexto da solicitação e recomeçar a partir do início."
        
        self.job_manager.set_job(job_id, job_info)
        print(f"[{job_id}] Job abortado por timeout - Status definido como 'failed'")