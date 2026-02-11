import redis
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from backend.app.core.config import settings
from backend.app.models.session_models import SessionData
import logging
from backend.app.models.job_models import JobData
from backend.app.services.azure_secret_manager import AzureSecretManager

class RedisSessionService:
    def __init__(self):
        logger = logging.getLogger("RedisSessionService")
        try:
            key_vault_url = getattr(settings, "KEY_VAULT_URL", None)
            if not key_vault_url:
                logger.critical("KEY_VAULT_URL não definido nas configurações.")
                raise EnvironmentError("KEY_VAULT_URL não definido.")
            secret_manager = AzureSecretManager(key_vault_url)
            redis_host = secret_manager.get_secret("redis-host")
            redis_port = int(secret_manager.get_secret("redis-port"))
            redis_password = secret_manager.get_secret("redis-password")
            redis_db = int(secret_manager.get_secret("redis-db"))
            redis_use_ssl = secret_manager.get_secret("redis-use-ssl")
            redis_ssl_cert_reqs = secret_manager.get_secret("redis-ssl-cert-reqs")
            # Converte redis_use_ssl para boolean
            if isinstance(redis_use_ssl, str):
                redis_use_ssl = redis_use_ssl.lower() in ["true", "1", "yes"]
        except Exception as e:
            logger.critical(f"Erro ao obter segredos do Redis do Key Vault: {e}")
            raise
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            db=redis_db,
            decode_responses=True,
            ssl=redis_use_ssl,
            ssl_cert_reqs=redis_ssl_cert_reqs
        )
        self.session_ttl = int(getattr(settings, 'REDIS_SESSION_TTL', 86400))
        self.logger = logger

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

    def create_session(self, email: str, empresa: str, usuario_executor: str, nome_projeto: str, project_id: str) -> str:
        key = f"project:{project_id}:resumo"
        created_at = datetime.utcnow().isoformat()
        session_data = {
            "email": email,
            "empresa": empresa,
            "usuario_executor": usuario_executor,
            "nome_projeto": nome_projeto,
            "created_at": created_at,
            "project_id": project_id
        }
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))
        return project_id

    def create_job(self, project_id: str, analysis_type: str, email: str = None, empresa: str = None) -> str:
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
            completed_at=None,
            email=email,
            empresa=empresa
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

    def _update_timestamps(self, data: dict, status: str):
        data['status'] = status
        data['updated_at'] = datetime.utcnow().isoformat()
        if status == 'done':
            now_iso = datetime.utcnow().isoformat()
            data['response_timestamp'] = now_iso
            if not data.get('completed_at'):
                data['completed_at'] = now_iso

    def update_job_status(self, job_id: str, status: str):
        key = f"job:{job_id}"
        job_json = self.redis_client.get(key)
        if not job_json:
            self.logger.error(f"Job {job_id} não encontrado para atualização de status.")
            return
        try:
            data = json.loads(job_json)
            self._update_timestamps(data, status)
            self.redis_client.setex(key, self.session_ttl, json.dumps(data))
        except Exception as e:
            self.logger.error(f"Erro ao atualizar status do job {job_id}: {e}")

    def store_report_data_for_job(self, job_id: str, report_data: dict):
        key = f"job:{job_id}:report"
        try:
            self.redis_client.setex(key, self.session_ttl, json.dumps(report_data))
        except Exception as e:
            self.logger.error(f"Erro ao armazenar report_data para job {job_id}: {e}")

    def get_report_data_for_job(self, job_id: str) -> Optional[dict]:
        key = f"job:{job_id}:report"
        report_json = self.redis_client.get(key)
        if report_json:
            try:
                return json.loads(report_json)
            except Exception as e:
                self.logger.error(f"Erro ao desserializar report_data para job {job_id}: {e}")
                return None
        return None

    def store_error_message_for_job(self, job_id: str, error_message: str):
        key = f"job:{job_id}:error"
        try:
            self.redis_client.setex(key, self.session_ttl, json.dumps({"error_message": error_message}))
        except Exception as e:
            self.logger.error(f"Erro ao armazenar error_message para job {job_id}: {e}")
