import redis
import json
from typing import Dict, Any, Optional

class JobHandler:
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client

    def get_job_info(self, job_id: str) -> Dict[str, Any]:
        job_data = self.redis_client.get(f"job:{job_id}")
        if job_data:
            return json.loads(job_data)
        return {}

    def update_job(self, job_id: str, job_info: Dict[str, Any]) -> None:
        self.redis_client.set(f"job:{job_id}", json.dumps(job_info))

    def update_job_status(self, job_id: str, status: str) -> None:
        job_info = self.get_job_info(job_id)
        job_info['status'] = status
        self.update_job(job_id, job_info)

    def set_paused_step(self, job_info: Dict[str, Any], step_index: int) -> None:
        if 'data' not in job_info:
            job_info['data'] = {}
        job_info['data']['paused_at_step'] = step_index

    def get_step_result(self, job_info: Dict[str, Any], step_index: int) -> Optional[Dict[str, Any]]:
        steps = job_info.get('steps', [])
        if 0 <= step_index < len(steps):
            return steps[step_index]
        return None
