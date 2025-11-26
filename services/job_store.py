class JobStore:
    def __init__(self, backend):
        self.backend = backend

    def set_job(self, job_id, job_data):
        self.backend.set(job_id, job_data)

    def get_job(self, job_id):
        return self.backend.get(job_id)
