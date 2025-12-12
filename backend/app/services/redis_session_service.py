import redis
import json
import logging
from typing import Any, Dict, Optional
from backend.app.core.config import settings

class RedisSessionService:
    def __init__(self):
        self.client = redis.StrictRedis.from_url(settings.REDIS_URL, decode_responses=True)
        self.logger = logging.getLogger("RedisSessionService")

    def update_report(self, project_id: str, report_data: Dict[str, Any], job_id: Optional[str] = None):
        session_key = f"session:{project_id}"
        session_json = self.client.get(session_key)
        if session_json:
            session_data = json.loads(session_json)
        else:
            session_data = {}
        # Adiciona o job_id ao report_data se fornecido
        if job_id:
            for k in report_data:
                if isinstance(report_data[k], dict):
                    report_data[k]["job_id"] = job_id
                else:
                    report_data[k] = {"data": report_data[k], "job_id": job_id}
        # Atualiza o session_data com o novo report_data
        session_data.update(report_data)
        # Propaga o job_id no nível da sessão para facilitar persistência
        if job_id:
            session_data["job_id"] = job_id
        self.client.set(session_key, json.dumps(session_data, ensure_ascii=False))

    def get_session_by_project_id(self, project_id: str) -> Any:
        session_key = f"session:{project_id}"
        session_json = self.client.get(session_key)
        if session_json:
            return json.loads(session_json)
        return None

    def update_job_status(self, job_id: str, status: str):
        job_key = f"job:{job_id}:status"
        self.client.set(job_key, status)

    def get_active_job_for_project(self, project_id: str) -> Any:
        # Implementação simplificada para exemplo
        active_job_key = f"active_job:{project_id}"
        job_json = self.client.get(active_job_key)
        if job_json:
            return json.loads(job_json)
        return None
