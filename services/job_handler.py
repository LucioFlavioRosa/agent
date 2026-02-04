from utils.constants import JOB_NOT_FOUND_ERROR, STEP_RESULT_KEY_FORMAT, PAUSED_AT_STEP_KEY, INSTRUCOES_EXTRAS_APROVACAO_KEY
from domain.interfaces.job_manager_interface import IJobManager
from services.base_service import BaseService

class JobHandler(BaseService):
    def __init__(self, job_manager: IJobManager):
        super().__init__()
        self.job_manager = job_manager

    def get_job_info(self, job_id: str):
        job_info = self.job_manager.get_job(job_id)
        if not job_info:
            raise ValueError(JOB_NOT_FOUND_ERROR)
        return job_info

    def update_job_status(self, job_id: str, status: str):
        self.job_manager.update_job_status(job_id, status)

    def update_job(self, job_id: str, job_info):
        self.job_manager.update_job(job_id, job_info)

    def handle_job_error(self, job_id: str, error: Exception, context: str):
        self.job_manager.handle_job_error(job_id, error, context)

    def save_step_result(self, job_info, step_index: int, step_result):
        job_info['data'][STEP_RESULT_KEY_FORMAT.format(step_index=step_index)] = step_result

    def get_step_result(self, job_info, step_index: int):
        return job_info['data'].get(STEP_RESULT_KEY_FORMAT.format(step_index=step_index - 1), {})

    def should_generate_report_only(self, job_info, current_step_index: int):
        return current_step_index == 0 and job_info['data'].get('gerar_relatorio_apenas') is True

    def set_approval_instructions(self, job_info, instructions: str):
        job_info['data'][INSTRUCOES_EXTRAS_APROVACAO_KEY] = instructions

    def get_approval_instructions(self, job_info):
        return job_info['data'].get(INSTRUCOES_EXTRAS_APROVACAO_KEY)

    def clear_approval_instructions(self, job_info):
        job_info['data'][INSTRUCOES_EXTRAS_APROVACAO_KEY] = None

    def set_paused_step(self, job_info, step_index: int):
        job_info['data'][PAUSED_AT_STEP_KEY] = step_index
