from typing import List, Dict, Any, Optional
from models import JobFields

class JobHandler:
    def __init__(self, job_manager):
        self.job_manager = job_manager

    def get_job_info(self, job_id: str) -> Dict[str, Any]:
        return self.job_manager.get_job(job_id)

    def update_job(self, job_id: str, job_info: Dict[str, Any]) -> None:
        self.job_manager.set_job(job_id, job_info)

    def update_job_status(self, job_id: str, status: str) -> None:
        job_info = self.get_job_info(job_id)
        job_info[JobFields.STATUS] = status
        self.update_job(job_id, job_info)

    def save_step_result(self, job_info: Dict[str, Any], step_index: int, step_result: Dict[str, Any]) -> None:
        if 'step_results' not in job_info[JobFields.DATA]:
            job_info[JobFields.DATA]['step_results'] = {}
        job_info[JobFields.DATA]['step_results'][step_index] = step_result

    def handle_job_error(self, job_id: str, error: Exception, context: str) -> None:
        job_info = self.get_job_info(job_id)
        job_info[JobFields.ERROR_DETAILS] = f"[{context}] {str(error)}"
        self.update_job(job_id, job_info)
        self.update_job_status(job_id, 'failed')

    def set_paused_step(self, job_info: Dict[str, Any], step_index: int) -> None:
        job_info[JobFields.DATA][JobFields.PAUSED_AT_STEP] = step_index

    def get_approval_instructions(self, job_info: Dict[str, Any]) -> Optional[str]:
        return job_info[JobFields.DATA].get(JobFields.INSTRUCOES_EXTRAS_APROVACAO)

    def clear_approval_instructions(self, job_info: Dict[str, Any]) -> None:
        job_info[JobFields.DATA][JobFields.INSTRUCOES_EXTRAS_APROVACAO] = None

    def save_epic_ids(self, job_id: str, epic_ids: List[str], epics_created: Optional[List[Dict[str, Any]]] = None) -> None:
        job_info = self.get_job_info(job_id)
        job_info[JobFields.DATA][JobFields.EPIC_IDS] = epic_ids
        if epics_created is not None:
            job_info[JobFields.DATA][JobFields.EPICS_CREATED] = epics_created
        self.update_job(job_id, job_info)
