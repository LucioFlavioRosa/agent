import os
import json
from typing import Dict, Any

class JobStore:
    """
    Gerencia o estado dos jobs para o MCP Azure Board.
    Implementação básica baseada em arquivo local (pode ser adaptada para outros backends).
    """
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or os.getenv('JOB_STORE_PATH', './job_store.json')
        self._jobs: Dict[str, Any] = self._load_jobs()

    def _load_jobs(self) -> Dict[str, Any]:
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_jobs(self):
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self._jobs, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_job(self, job_id: str) -> Any:
        return self._jobs.get(job_id)

    def set_job(self, job_id: str, job_data: Any):
        self._jobs[job_id] = job_data
        self._save_jobs()

    def delete_job(self, job_id: str):
        if job_id in self._jobs:
            del self._jobs[job_id]
            self._save_jobs()

    def list_jobs(self):
        return list(self._jobs.keys())
