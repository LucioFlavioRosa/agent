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
        self.logger = logging.getLogger("RedisSessionService")
        try:
            key_vault_url = getattr(settings, "KEY_VAULT_URL", None)
            if not key_vault_url:
                self.logger.critical("KEY_VAULT_URL não definido nas configurações.")
                raise EnvironmentError("KEY_VAULT_URL não definido.")
            secret_manager = AzureSecretManager(key_vault_url)
            redis_host = secret_manager.get_secret("redis-host")
            redis_port = int(secret_manager.get_secret("redis-port"))
            redis_password = secret_manager.get_secret("redis-password")
            redis_db = int(secret_manager.get_secret("redis-db"))
            redis_use_ssl = secret_manager.get_secret("redis-use-ssl")
            redis_ssl_cert_reqs = secret_manager.get_secret("redis-ssl-cert-reqs")
            if isinstance(redis_use_ssl, str):
                redis_use_ssl = redis_use_ssl.lower() in ["true", "1", "yes"]
        except Exception as e:
            self.logger.critical(f"Erro ao obter segredos do Redis do Key Vault: {e}")
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

    def _serialize_session(self, session_data: dict) -> str:
        return json.dumps(session_data)

    def _deserialize_session(self, session_json: str) -> dict:
        return json.loads(session_json)

    def get_session_by_project_id(self, project_id: str) -> Optional[SessionData]:
        key = f"project:{project_id}:resumo"
        self.logger.info(f"[get_session_by_project_id] Buscando sessão para project_id '{project_id}' (chave Redis: '{key}')")
        session_json = self.redis_client.get(key)
        if session_json:
            try:
                self.logger.info(f"[get_session_by_project_id] Dados encontrados: {session_json}")
                return SessionData(**self._deserialize_session(session_json))
            except Exception as e:
                self.logger.error(f"[get_session_by_project_id] Erro ao converter dados do Redis para SessionData: {e}")
                return None
        self.logger.warning(f"[get_session_by_project_id] Nenhuma sessão encontrada para project_id '{project_id}'.")
        return None

    def create_session(self, email: str, empresa: str, usuario_executor: str, nome_projeto: str, project_id: str) -> str:
        key = f"project:{project_id}:resumo"
        self.logger.info(f"[create_session] Criando sessão para project_id '{project_id}' (chave Redis: '{key}'). Dados: email='{email}', empresa='{empresa}', usuario_executor='{usuario_executor}', nome_projeto='{nome_projeto}'")
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
        self.logger.info(f"[create_session] Sessão criada e armazenada no Redis para project_id '{project_id}'.")
        return project_id

    def create_job(self, project_id: str, analysis_type: str, email: str = None, empresa: str = None) -> str:
        self.logger.info(f"[create_job] Iniciando criação de job para project_id '{project_id}', analysis_type '{analysis_type}', email '{email}', empresa '{empresa}'")
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
        self.logger.info(f"[create_job] Armazenando job no Redis (chave: '{key}'). Dados: {job}")
        self.redis_client.setex(key, self.session_ttl, job.json())
        self.logger.info(f"[create_job] Job criado e armazenado com sucesso. job_id: '{job_id}'")
        return job_id

    def get_job(self, job_id: str) -> Optional[JobData]:
        key = f"job:{job_id}"
        self.logger.info(f"[get_job] Buscando job no Redis (chave: '{key}')")
        job_json = self.redis_client.get(key)
        if job_json:
            try:
                data = json.loads(job_json)
                self.logger.info(f"[get_job] Dados encontrados: {data}")
                return JobData(**data)
            except Exception as e:
                self.logger.error(f"[get_job] Erro ao desserializar JobData do Redis: {e}")
                return None
        self.logger.warning(f"[get_job] Nenhum job encontrado para job_id '{job_id}'.")
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
        self.logger.info(f"[update_job_status] Atualizando status do job_id '{job_id}' para '{status}' (chave Redis: '{key}')")
        job_json = self.redis_client.get(key)
        if not job_json:
            self.logger.error(f"[update_job_status] Job '{job_id}' não encontrado para atualização de status.")
            return
        try:
            data = json.loads(job_json)
            self.logger.info(f"[update_job_status] Dados atuais do job: {data}")
            self._update_timestamps(data, status)
            self.redis_client.setex(key, self.session_ttl, json.dumps(data))
            self.logger.info(f"[update_job_status] Status do job atualizado para '{status}' e armazenado no Redis.")
        except Exception as e:
            self.logger.error(f"[update_job_status] Erro ao atualizar status do job '{job_id}': {e}")

    def store_report_data_for_job(self, job_id: str, report_data: dict):
        key = f"job:{job_id}:report"
        self.logger.info(f"[store_report_data_for_job] Armazenando report_data para job_id '{job_id}' (chave Redis: '{key}'). Dados: {report_data}")
        try:
            self.redis_client.setex(key, self.session_ttl, json.dumps(report_data))
            self.logger.info(f"[store_report_data_for_job] report_data armazenado com sucesso para job_id '{job_id}'.")
        except Exception as e:
            self.logger.error(f"[store_report_data_for_job] Erro ao armazenar report_data para job '{job_id}': {e}")

    def get_report_data_for_job(self, job_id: str) -> Optional[dict]:
        key = f"job:{job_id}:report"
        self.logger.info(f"[get_report_data_for_job] Buscando report_data para job_id '{job_id}' (chave Redis: '{key}')")
        report_json = self.redis_client.get(key)
        if report_json:
            try:
                self.logger.info(f"[get_report_data_for_job] Dados encontrados: {report_json}")
                return json.loads(report_json)
            except Exception as e:
                self.logger.error(f"[get_report_data_for_job] Erro ao desserializar report_data para job '{job_id}': {e}")
                return None
        self.logger.warning(f"[get_report_data_for_job] Nenhum report_data encontrado para job_id '{job_id}'.")
        return None

    def store_error_message_for_job(self, job_id: str, error_message: str):
        key = f"job:{job_id}:error"
        self.logger.info(f"[store_error_message_for_job] Armazenando error_message para job_id '{job_id}' (chave Redis: '{key}'). Mensagem: {error_message}")
        try:
            self.redis_client.setex(key, self.session_ttl, json.dumps({"error_message": error_message}))
            self.logger.info(f"[store_error_message_for_job] error_message armazenado com sucesso para job_id '{job_id}'.")
        except Exception as e:
            self.logger.error(f"[store_error_message_for_job] Erro ao armazenar error_message para job '{job_id}': {e}")
