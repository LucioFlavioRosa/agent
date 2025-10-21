from typing import Any, Dict, List, Optional

class JobHandler:
    def __init__(self, job_manager):
        self.job_manager = job_manager

    def get_job_info(self, job_id: str) -> Dict[str, Any]:
        return self.job_manager.get_job(job_id)

    def update_job(self, job_id: str, job_info: Dict[str, Any]) -> None:
        self.job_manager.update_job(job_id, job_info)

    def update_job_status(self, job_id: str, status: str) -> None:
        job_info = self.get_job_info(job_id)
        job_info['status'] = status
        self.update_job(job_id, job_info)

    def save_step_result(self, job_info: Dict[str, Any], step_index: int, step_result: Dict[str, Any]) -> None:
        if 'step_results' not in job_info['data']:
            job_info['data']['step_results'] = {}
        job_info['data']['step_results'][step_index] = step_result

    def set_paused_step(self, job_info: Dict[str, Any], step_index: int) -> None:
        job_info['data']['paused_at_step'] = step_index
        
    def get_step_result(self, job_info: Dict[str, Any], step_index: int) -> Dict[str, Any]:
        return job_info['data'].get(f'step_{step_index - 1}_result', {})

    def handle_job_error(self, job_id: str, error: Exception, context: str = None) -> None:
        job_info = self.get_job_info(job_id)
        job_info['status'] = 'failed'
        job_info['error_details'] = str(error)
        self.update_job(job_id, job_info)

    def get_approval_instructions(self, job_info: Dict[str, Any]) -> Optional[str]:
        return job_info['data'].get('instrucoes_extras_aprovacao')

    def clear_approval_instructions(self, job_info: Dict[str, Any]) -> None:
        if 'instrucoes_extras_aprovacao' in job_info['data']:
            job_info['data'].pop('instrucoes_extras_aprovacao')

    def save_epic_ids(self, job_id: str, epic_ids: List[str], epics: Optional[List[Dict[str, Any]]] = None) -> None:
        job_info = self.get_job_info(job_id)
        job_info['data']['epic_ids'] = epic_ids
        if epics is not None:
            job_info['data']['epics'] = epics
        self.update_job(job_id, job_info)
