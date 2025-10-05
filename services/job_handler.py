from mcp_server_fastapi import JobFields
class JobHandler:
    def __init__(self, job_manager):
        self.job_manager = job_manager
    def get_job_info(self, job_id):
        return self.job_manager.get_job(job_id)
    def get_step_result(self, job_info, step_index):
        return job_info.get('step_results', {}).get(str(step_index))
    def save_step_result(self, job_info, step_index, step_result):
        if 'step_results' not in job_info:
            job_info['step_results'] = {}
        job_info['step_results'][str(step_index)] = step_result
    def update_job_status(self, job_id, status):
        job_info = self.job_manager.get_job(job_id)
        job_info[JobFields.STATUS] = status
        self.job_manager.set_job(job_id, job_info)
    def update_job(self, job_id, job_info):
        self.job_manager.set_job(job_id, job_info)
    def set_paused_step(self, job_info, step_index):
        job_info['data'][JobFields.PAUSED_AT_STEP] = step_index
    def handle_job_error(self, job_id, exception, context):
        job_info = self.job_manager.get_job(job_id)
        job_info[JobFields.STATUS] = 'failed'
        job_info[JobFields.ERROR_DETAILS] = str(exception)
        self.job_manager.set_job(job_id, job_info)
