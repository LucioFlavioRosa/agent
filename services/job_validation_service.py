class JobValidationService:
    def validate_job_exists(self, job, job_id):
        if not job:
            raise Exception(f"Job {job_id} não encontrado.")

    def validate_job_for_approval(self, job, job_id):
        if not job:
            raise Exception(f"Job {job_id} não encontrado para aprovação.")
        if job.get('status') != 'pending_approval':
            raise Exception(f"Job {job_id} não está aguardando aprovação.")
