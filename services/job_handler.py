import time
from typing import Dict, Any, Optional
from domain.interfaces.job_manager_interface import IJobManager

class JobHandler:
    def __init__(self, job_manager: IJobManager):
        self.job_manager = job_manager
    
    def get_job_info(self, job_id: str) -> Dict[str, Any]:
        job = self.job_manager.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} não encontrado")
        return job
    
    def update_job_status(self, job_id: str, status: str) -> None:
        job = self.job_manager.get_job(job_id)
        if job:
            job['status'] = status
            job['last_status_update'] = time.time()
            self.job_manager.set_job(job_id, job)
    
    def update_job(self, job_id: str, job_data: Dict[str, Any]) -> None:
        self.job_manager.set_job(job_id, job_data)
    
    def get_step_result(self, job_info: Dict[str, Any], start_from_step: int) -> Dict[str, Any]:
        if start_from_step == 0:
            return {}
        
        step_results = job_info.get('data', {}).get('step_results', {})
        previous_step_key = f'step_{start_from_step - 1}'
        return step_results.get(previous_step_key, {})
    
    def save_step_result(self, job_info: Dict[str, Any], step_index: int, result: Dict[str, Any]) -> None:
        if 'step_results' not in job_info['data']:
            job_info['data']['step_results'] = {}
        
        step_key = f'step_{step_index}'
        job_info['data']['step_results'][step_key] = result
    
    def get_approval_instructions(self, job_info: Dict[str, Any]) -> Optional[str]:
        return job_info.get('data', {}).get('instrucoes_extras_aprovacao')
    
    def clear_approval_instructions(self, job_info: Dict[str, Any]) -> None:
        if 'instrucoes_extras_aprovacao' in job_info.get('data', {}):
            del job_info['data']['instrucoes_extras_aprovacao']
    
    def set_paused_step(self, job_info: Dict[str, Any], step_index: int) -> None:
        job_info['data']['paused_at_step'] = step_index
    
    def handle_job_error(self, job_id: str, error: Exception, context: str) -> None:
        try:
            job = self.job_manager.get_job(job_id)
            if job:
                job['status'] = 'failed'
                job['last_status_update'] = time.time()
                job['error_details'] = f"Erro em {context}: {str(error)}"
                self.job_manager.set_job(job_id, job)
        except Exception as e:
            print(f"[{job_id}] ERRO ao salvar erro do job: {str(e)}")
    
    def abort_job_due_to_timeout(self, job_id: str, job_data: Dict[str, Any]) -> None:
        try:
            job_data['status'] = 'failed'
            job_data['last_status_update'] = time.time()
            job_data['error_details'] = "O workflow foi abortado por inatividade (timeout de 6 minutos). Considere reduzir o contexto da solicitação e recomeçar a partir do início."
            
            self.job_manager.set_job(job_id, job_data)
            print(f"[{job_id}] Job abortado por timeout - mensagem registrada para o usuário")
            
        except Exception as e:
            print(f"[{job_id}] ERRO ao abortar job por timeout: {str(e)}")