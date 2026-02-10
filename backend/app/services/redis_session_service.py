import redis
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from backend.app.core.config import settings
from backend.app.models.session_models import SessionData
import logging
from backend.app.models.job_models import JobData

class RedisSessionService:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=getattr(settings, 'REDIS_HOST', 'localhost'),
            port=int(getattr(settings, 'REDIS_PORT', 6379)),
            password=getattr(settings, 'REDIS_PASSWORD', None),
            db=int(getattr(settings, 'REDIS_DB', 0)),
            decode_responses=True,
            ssl=getattr(settings, 'REDIS_USE_SSL', True),
            ssl_cert_reqs=getattr(settings, 'REDIS_SSL_CERT_REQS', 'required')
        )
        self.session_ttl = int(getattr(settings, 'REDIS_SESSION_TTL', 86400))
        self.logger = logging.getLogger("RedisSessionService")

    def _serialize_session(self, session_data: dict) -> str:
        return json.dumps(session_data)

    def _deserialize_session(self, session_json: str) -> dict:
        return json.loads(session_json)

    def get_session_by_project_id(self, project_id: str) -> Optional[SessionData]:
        key = f"project:{project_id}:resumo"
        session_json = self.redis_client.get(key)
        if session_json:
            try:
                return SessionData(**self._deserialize_session(session_json))
            except Exception as e:
                self.logger.error(f"Erro ao converter dados do Redis para SessionData: {e}")
                return None
        return None

    def create_session(self, usuario_executor: str, nome_projeto: str, project_id: str) -> str:
        key = f"project:{project_id}:resumo"
        created_at = datetime.utcnow().isoformat()
        session_data = {
            "usuario_executor": usuario_executor,
            "nome_projeto": nome_projeto,
            "created_at": created_at,
            "project_id": project_id
        }
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))
        return project_id

    def create_job(self, project_id: str, analysis_type: str) -> str:
        job_id = str(uuid.uuid4())
        now = datetime.utcnow()
        job = JobData(
            job_id=job_id,
            project_id=project_id,
            analysis_type=analysis_type,
            status='pending',
            created_at=now,
            updated_at=now,
            request_timestamp=now,
            response_timestamp=None,
            completed_at=None
        )
        key = f"job:{job_id}"
        self.redis_client.setex(key, self.session_ttl, job.json())
        return job_id

    def get_job(self, job_id: str) -> Optional[JobData]:
        key = f"job:{job_id}"
        job_json = self.redis_client.get(key)
        if job_json:
            try:
                data = json.loads(job_json)
                return JobData(**data)
            except Exception as e:
                self.logger.error(f"Erro ao desserializar JobData do Redis: {e}")
                return None
        return None

    def update_job_status(self, job_id: str, status: str):
        key = f"job:{job_id}"
        job_json = self.redis_client.get(key)
        if not job_json:
            self.logger.error(f"Job {job_id} não encontrado para atualização de status.")
            return
        try:
            data = json.loads(job_json)
            previous_status = data.get('status')
            data['status'] = status
            data['updated_at'] = datetime.utcnow().isoformat()
            if status == 'done':
                now_iso = datetime.utcnow().isoformat()
                data['response_timestamp'] = now_iso
                if not data.get('completed_at'):
                    data['completed_at'] = now_iso
            self.redis_client.setex(key, self.session_ttl, json.dumps(data))
        except Exception as e:
            self.logger.error(f"Erro ao atualizar status do job {job_id}: {e}")

    def get_active_job_for_project(self, project_id: str) -> Optional[JobData]:
        pattern = f"job:*"
        job_keys = self.redis_client.keys(pattern)
        jobs: List[JobData] = []
        TOLERANCIA_MINUTOS = 10
        for key in job_keys:
            job_json = self.redis_client.get(key)
            if not job_json:
                continue
            try:
                data = json.loads(job_json)
                if (
                    data.get('project_id') == project_id and
                    data.get('status') in ('pending', 'in_progress')
                ):
                    job = JobData(**data)
                    updated_at = job.updated_at
                    if isinstance(updated_at, str):
                        updated_at = datetime.fromisoformat(updated_at)
                    tempo_ocioso = (datetime.utcnow() - updated_at).total_seconds() / 60
                    if tempo_ocioso > TOLERANCIA_MINUTOS:
                        self.logger.warning(f"Ignorando Job Zumbi {job.job_id}: Ativo há {tempo_ocioso:.1f} min sem atualização.")
                        continue
                    jobs.append(job)
            except Exception:
                continue
        if not jobs:
            return None
        jobs.sort(key=lambda j: j.request_timestamp if hasattr(j, 'request_timestamp') and j.request_timestamp else datetime.min, reverse=True)
        return jobs[0]

    def get_latest_done_job_for_project(self, project_id: str) -> Optional[JobData]:
        pattern = f"job:*"
        job_keys = self.redis_client.keys(pattern)
        jobs: List[JobData] = []
        for key in job_keys:
            job_json = self.redis_client.get(key)
            if not job_json:
                continue
            try:
                data = json.loads(job_json)
                if data.get('project_id') == project_id and data.get('status') == 'done':
                    jobs.append(JobData(**data))
            except Exception:
                continue
        if not jobs:
            return None
        jobs.sort(key=lambda j: j.response_timestamp if hasattr(j, 'response_timestamp') and j.response_timestamp else datetime.min, reverse=True)
        return jobs[0]

    def get_latest_completed_job_for_project(self, project_id: str) -> Optional[JobData]:
        pattern = f"job:*"
        job_keys = self.redis_client.keys(pattern)
        jobs: List[JobData] = []
        for key in job_keys:
            job_json = self.redis_client.get(key)
            if not job_json:
                continue
            try:
                data = json.loads(job_json)
                if data.get('project_id') == project_id and data.get('status') == 'done':
                    jobs.append(JobData(**data))
            except Exception:
                continue
        if not jobs:
            return None
        def sort_key(j):
            if hasattr(j, 'completed_at') and j.completed_at:
                try:
                    return j.completed_at if isinstance(j.completed_at, datetime) else datetime.fromisoformat(str(j.completed_at))
                except Exception:
                    return datetime.min
            elif hasattr(j, 'response_timestamp') and j.response_timestamp:
                try:
                    return j.response_timestamp if isinstance(j.response_timestamp, datetime) else datetime.fromisoformat(str(j.response_timestamp))
                except Exception:
                    return datetime.min
            return datetime.min
        jobs.sort(key=sort_key, reverse=True)
        return jobs[0]
