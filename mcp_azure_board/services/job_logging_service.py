import logging
import json
import os
from datetime import datetime

class JobLoggingService:
    def __init__(self, log_dir=None):
        self.log_dir = log_dir or os.getenv('JOB_LOG_DIR', './logs')
        os.makedirs(self.log_dir, exist_ok=True)
        self.logger = logging.getLogger('JobLogger')
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.FileHandler(os.path.join(self.log_dir, 'jobs.log'))
            formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_starting_job(self, job_id, payload, repo_name, analysis_name):
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': 'starting_job',
            'job_id': job_id,
            'repo_name': repo_name,
            'analysis_name': analysis_name,
            'payload': payload
        }
        self.logger.info(json.dumps(entry))

    def log_job_status(self, job_id, status, details=None):
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': 'job_status',
            'job_id': job_id,
            'status': status,
            'details': details
        }
        self.logger.info(json.dumps(entry))

    def log_job_error(self, job_id, error_message, details=None):
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': 'job_error',
            'job_id': job_id,
            'error_message': error_message,
            'details': details
        }
        self.logger.error(json.dumps(entry))
