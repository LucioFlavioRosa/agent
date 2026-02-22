import redis.asyncio as redis  # Importação da versão assíncrona
import uuid
import json
from datetime import datetime
from typing import Optional
from backend.app.core.config import settings
from backend.app.models.session_models import SessionData
import logging
from backend.app.models.job_models import JobData
from backend.app.models.permission_models import UserPermissionCache

class RedisSessionService:
    def __init__(self):
        self.logger = logging.getLogger("RedisSessionService")
        
        # Lê direto do settings carregado na memória
        redis_use_ssl_val = settings.REDIS_USE_SSL
        if isinstance(redis_use_ssl_val, str):
             redis_use_ssl_val = redis_use_ssl_val.lower() in ["true", "1", "yes"]

        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=int(settings.REDIS_PORT or 6379),
            password=settings.REDIS_PASSWORD,
            db=int(settings.REDIS_DB or 0),
            ssl=redis_use_ssl_val,
            ssl_cert_reqs=settings.REDIS_SSL_CERT_REQS,
            decode_responses=True,
            socket_connect_timeout=3.0, 
            socket_timeout=3.0
        )
        self.session_ttl = int(getattr(settings, 'REDIS_PERM_TTL', 600))

    # --- Métodos Auxiliares Síncronos ---
    def _serialize_session(self, session_data: dict) -> str:
        return json.dumps(session_data)

    def _deserialize_session(self, session_json: str) -> dict:
        return json.loads(session_json)

    def _update_timestamps(self, data: dict, status: str):
        data['status'] = status
        data['updated_at'] = datetime.utcnow().isoformat()
        if status == 'done':
            now_iso = datetime.utcnow().isoformat()
            data['response_timestamp'] = now_iso
            if not data.get('completed_at'):
                data['completed_at'] = now_iso

    # --- Métodos Assíncronos (I/O com o Redis) ---

    async def get_session_by_project_id(self, project_id: str) -> Optional[SessionData]:
        key = f"project:{project_id}:resumo"
        self.logger.info(f"[get_session_by_project_id] Buscando sessão para project_id '{project_id}'")
        
        session_json = await self.redis_client.get(key)
        
        if session_json:
            try:
                return SessionData(**self._deserialize_session(session_json))
            except Exception as e:
                self.logger.error(f"[get_session_by_project_id] Erro ao converter dados do Redis: {e}")
                return None
        return None

    async def create_session(self, email: str, empresa: str, usuario_executor: str, nome_projeto: str, project_id: str) -> str:
        key = f"project:{project_id}:resumo"
        self.logger.info(f"[create_session] Criando sessão para '{project_id}'...")
        session_data = {
            "email": email,
            "empresa": empresa,
            "usuario_executor": usuario_executor,
            "nome_projeto": nome_projeto,
            "created_at": datetime.utcnow().isoformat(),
            "project_id": project_id
        }
        
        await self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))
        return project_id

    async def create_job(self, project_id: str, analysis_type: str, email: str = None, empresa: str = None) -> str:
        self.logger.info(f"[create_job] Iniciando criação de job para project_id '{project_id}'...")
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
        
        await self.redis_client.setex(key, self.session_ttl, job.json())
        return job_id

    async def get_job(self, job_id: str) -> Optional[JobData]:
        key = f"job:{job_id}"
        self.logger.info(f"[get_job] Buscando job no Redis (chave: '{key}')")
        
        job_json = await self.redis_client.get(key)
        
        if job_json:
            try:
                data = json.loads(job_json)
                return JobData(**data)
            except Exception as e:
                self.logger.error(f"[get_job] Erro ao desserializar JobData do Redis: {e}")
                return None
        return None

    async def update_job_status(self, job_id: str, status: str):
        key = f"job:{job_id}"
        self.logger.info(f"[update_job_status] Atualizando status do '{job_id}' para '{status}'")
        
        job_json = await self.redis_client.get(key)
        
        if not job_json:
            self.logger.error(f"[update_job_status] Job '{job_id}' não encontrado.")
            return
        try:
            data = json.loads(job_json)
            self._update_timestamps(data, status)
            
            await self.redis_client.setex(key, self.session_ttl, json.dumps(data))
        except Exception as e:
            self.logger.error(f"[update_job_status] Erro ao atualizar status do job '{job_id}': {e}")

    # --- Tratamento de Erros de Job ---
    async def store_error_message_for_job(self, job_id: str, error_message: str):
        key = f"job:{job_id}:error"
        self.logger.info(f"[store_error_message_for_job] Armazenando erro para '{job_id}'.")
        try:
            await self.redis_client.setex(key, self.session_ttl, json.dumps({"error_message": error_message}))
        except Exception as e:
            self.logger.error(f"[store_error_message_for_job] Erro ao armazenar: {e}")

    async def get_error_message_for_job(self, job_id: str) -> Optional[str]:
        key = f"job:{job_id}:error"
        self.logger.info(f"[get_error_message_for_job] Buscando erro para '{job_id}'.")
        try:
            error_json = await self.redis_client.get(key)
            if error_json:
                data = json.loads(error_json)
                return data.get("error_message")
            return None
        except Exception as e:
            self.logger.error(f"[get_error_message_for_job] Erro ao recuperar: {e}")
            return None

    # --- Gestão de Cache de Permissões ---
    async def store_user_permissions(self, email: str, company_id: str, permissions: dict):
        key = f"perm:{email}:{company_id}"
        self.logger.info(f"[store_user_permissions] Cacheando permissões para {key}")
        try:
            ttl = int(getattr(settings, 'REDIS_PERM_TTL', 600))
            
            cache_data = permissions.copy()
            cache_data["email"] = email
            cache_data["company_id"] = company_id
            cache_data["cached_at"] = datetime.utcnow().isoformat()
            
            cache_obj = UserPermissionCache(**cache_data)
            
            await self.redis_client.setex(key, ttl, cache_obj.json())
        except Exception as e:
            self.logger.error(f"[store_user_permissions] Erro ao salvar cache: {e}")

    async def get_user_permissions(self, email: str, company_id: str) -> Optional[dict]:
        key = f"perm:{email}:{company_id}"
        
        perms_json = await self.redis_client.get(key) 
        
        if perms_json:
            try:
                cache_obj = UserPermissionCache.parse_raw(perms_json)
                return cache_obj.dict()
            except Exception as e:
                self.logger.error(f"[get_user_permissions] Erro ao carregar cache para {key}: {e}")
                return None
        return None

    async def invalidate_user_permissions(self, email: str, company_id: str):
        key = f"perm:{email}:{company_id}"
        self.logger.info(f"[invalidate_user_permissions] Limpando cache para {key}")
        await self.redis_client.delete(key)
