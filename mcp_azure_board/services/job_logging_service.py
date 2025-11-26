import logging
from typing import Any, Dict, Optional

class JobLoggingService:
    def __init__(self):
        self.logger = logging.getLogger("JobLoggingService")
        if not self.logger.hasHandlers():
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def log_starting_job(self, job_id: str, payload_dict: Dict[str, Any], normalized_repo_name: Optional[str], analysis_name: Optional[str]) -> None:
        self.logger.info(f"Iniciando job {job_id}: repo={normalized_repo_name}, analysis_name={analysis_name}, payload={payload_dict}")

    def log_job_status(self, job_id: str, status: str) -> None:
        self.logger.info(f"Job {job_id} status atualizado para: {status}")

    def log_error(self, job_id: str, error: str) -> None:
        self.logger.error(f"Erro no job {job_id}: {error}")
