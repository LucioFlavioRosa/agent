class JobStore:
    def __init__(self):
        self.jobs = {}
    def set_job(self, job_id, job_data):
        self.jobs[job_id] = job_data
    def get_job(self, job_id):
        return self.jobs.get(job_id)
