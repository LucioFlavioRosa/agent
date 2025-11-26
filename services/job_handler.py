class JobHandler:
    def __init__(self, job_manager):
        self.job_manager = job_manager

    def create_initial_job_data(self, payload_dict, normalized_repo_name, analysis_name):
        # Independente de plataforma, apenas dados genéricos
        job_data = {
            'data': payload_dict,
            'status': 'starting',
            'analysis_name': analysis_name,
            'repo_name_modernizado': normalized_repo_name,
        }
        return job_data

    def get_job_info(self, job_id):
        return self.job_manager.get_job(job_id)

    def update_job(self, job_id, job_info):
        self.job_manager.set_job(job_id, job_info)

    def update_job_status(self, job_id, status):
        job = self.get_job_info(job_id)
        job['status'] = status
        self.update_job(job_id, job)

    def set_paused_step(self, job_info, step_index):
        job_info['data']['paused_at_step'] = step_index

    def get_step_result(self, job_info, step_index):
        # Genérico, sem lógica específica de Azure ou código
        return job_info.get('data', {}).get('step_results', {}).get(step_index)
