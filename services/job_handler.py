import json
from typing import Dict, Any, Optional
from domain.interfaces.job_manager_interface import IJobManager

class JobHandler:
    def __init__(self, job_manager: IJobManager):
        self.job_manager = job_manager
    
    def get_job_info(self, job_id: str) -> Dict[str, Any]:
        job_info = self.job_manager.get_job(job_id)
        if not job_info:
            raise ValueError("Job não encontrado.")
        return job_info
    
    def update_job_status(self, job_id: str, status: str) -> None:
        self.job_manager.update_job_status(job_id, status)
    
    def update_job(self, job_id: str, job_info: Dict[str, Any]) -> None:
        self.job_manager.update_job(job_id, job_info)
    
    def handle_job_error(self, job_id: str, error: Exception, context: str) -> None:
        self.job_manager.handle_job_error(job_id, error, context)
    
    def save_step_result(self, job_info: Dict[str, Any], step_index: int, step_result: Dict[str, Any]) -> None:
        job_info['data'][f'step_{step_index}_result'] = step_result
    
    def get_step_result(self, job_info: Dict[str, Any], step_index: int) -> Dict[str, Any]:
        return job_info['data'].get(f'step_{step_index - 1}_result', {})
    
    def should_generate_report_only(self, job_info: Dict[str, Any], current_step_index: int) -> bool:
        return current_step_index == 0 and job_info['data'].get('gerar_relatorio_apenas') is True
    
    def set_approval_instructions(self, job_info: Dict[str, Any], instructions: str) -> None:
        job_info['data']['instrucoes_extras_aprovacao'] = instructions
    
    def get_approval_instructions(self, job_info: Dict[str, Any]) -> Optional[str]:
        return job_info['data'].get('instrucoes_extras_aprovacao')
    
    def clear_approval_instructions(self, job_info: Dict[str, Any]) -> None:
        job_info['data']['instrucoes_extras_aprovacao'] = None
    
    def set_paused_step(self, job_info: Dict[str, Any], step_index: int) -> None:
        job_info['data']['paused_at_step'] = step_index