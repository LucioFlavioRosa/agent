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

    def update_job_status(self, job_id, new_status):
        job = self.job_manager.get_job(job_id)
        old_status = job.get('status') if job else None
        print(f"[DEBUG] update_job_status: job_id={job_id}, old_status={old_status}, new_status={new_status}")
        if job:
            job['status'] = new_status
            self.job_manager.get_job(job_id, job)
            print(f"[DEBUG] Job {job_id} status atualizado para {new_status} no store.")

    def update_job(self, job_id, job_info):
        self.job_manager.get_job(job_id, job_info)

    def set_paused_step(self, job_info, step_index):
        job_info['data']['paused_at_step'] = step_index

    def handle_job_error(self, job_id, exception, context):
        job = self.job_manager.get_job(job_id)
        if job:
            job['status'] = 'failed'
            job['error_details'] = str(exception)
            self.job_manager.get_job(job_id, job)
