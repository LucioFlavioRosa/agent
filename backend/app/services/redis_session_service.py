import redis.asyncio as redis  # 1. MUDANÇA AQUI: Importação da versão assíncrona
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from backend.app.core.config import settings
from backend.app.models.session_models import SessionData
import logging
from backend.app.models.job_models import JobData
from backend.app.services.azure_secret_manager import AzureSecretManager
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

    # --- Métodos Auxiliares Síncronos (Apenas CPU, sem I/O de rede) ---
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
        self.logger.info(f"[get_session_by_project_id] Buscando sessão para project_id '{project_id}' (chave Redis: '{key}')")
        
        session_json = await self.redis_client.get(key) # 2. AWAIT AQUI
        
        if session_json:
            try:
                self.logger.info(f"[get_session_by_project_id] Dados encontrados: {session_json}")
                return SessionData(**self._deserialize_session(session_json))
            except Exception as e:
                self.logger.error(f"[get_session_by_project_id] Erro ao converter dados do Redis para SessionData: {e}")
                return None
        self.logger.warning(f"[get_session_by_project_id] Nenhuma sessão encontrada para project_id '{project_id}'.")
        return None

    async def create_session(self, email: str, empresa: str, usuario_executor: str, nome_projeto: str, project_id: str) -> str:
        key = f"project:{project_id}:resumo"
        self.logger.info(f"[create_session] Criando sessão para '{project_id}'...")
        created_at = datetime.utcnow().isoformat()
        session_data = {
            "email": email,
            "empresa": empresa,
            "usuario_executor": usuario_executor,
            "nome_projeto": nome_projeto,
            "created_at": created_at,
            "project_id": project_id
        }
        
        await self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data)) # AWAIT AQUI
        self.logger.info(f"[create_session] Sessão criada e armazenada no Redis para project_id '{project_id}'.")
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
        
        await self.redis_client.setex(key, self.session_ttl, job.json()) # AWAIT AQUI
        self.logger.info(f"[create_job] Job criado e armazenado com sucesso. job_id: '{job_id}'")
        return job_id

    async def get_job(self, job_id: str) -> Optional[JobData]:
        key = f"job:{job_id}"
        self.logger.info(f"[get_job] Buscando job no Redis (chave: '{key}')")
        
        job_json = await self.redis_client.get(key) # AWAIT AQUI
        
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

    async def update_job_status(self, job_id: str, status: str):
        key = f"job:{job_id}"
        self.logger.info(f"[update_job_status] Atualizando status do '{job_id}' para '{status}'")
        
        job_json = await self.redis_client.get(key) # AWAIT AQUI
        
        if not job_json:
            self.logger.error(f"[update_job_status] Job '{job_id}' não encontrado.")
            return
        try:
            data = json.loads(job_json)
            self._update_timestamps(data, status)
            
            await self.redis_client.setex(key, self.session_ttl, json.dumps(data)) # AWAIT AQUI
            self.logger.info(f"[update_job_status] Status do job atualizado para '{status}'.")
        except Exception as e:
            self.logger.error(f"[update_job_status] Erro ao atualizar status do job '{job_id}': {e}")

    async def store_report_data_for_job(self, job_id: str, report_data: dict):
        key = f"job:{job_id}:report"
        self.logger.info(f"[store_report_data_for_job] Armazenando report_data para '{job_id}'.")
        try:
            await self.redis_client.setex(key, self.session_ttl, json.dumps(report_data)) # AWAIT AQUI
        except Exception as e:
            self.logger.error(f"[store_report_data_for_job] Erro ao armazenar: {e}")

    async def get_report_data_for_job(self, job_id: str) -> Optional[dict]:
        key = f"job:{job_id}:report"
        self.logger.info(f"[get_report_data_for_job] Buscando report_data para '{job_id}'")
        
        report_json = await self.redis_client.get(key) # AWAIT AQUI
        
        if report_json:
            try:
                return json.loads(report_json)
            except Exception as e:
                self.logger.error(f"[get_report_data_for_job] Erro ao desserializar: {e}")
                return None
        return None

    async def store_error_message_for_job(self, job_id: str, error_message: str):
        key = f"job:{job_id}:error"
        self.logger.info(f"[store_error_message_for_job] Armazenando erro para '{job_id}'.")
        try:
            await self.redis_client.setex(key, self.session_ttl, json.dumps({"error_message": error_message})) # AWAIT AQUI
        except Exception as e:
            self.logger.error(f"[store_error_message_for_job] Erro ao armazenar: {e}")

    async def store_user_permissions(self, email: str, company_id: str, permissions: dict):
        key = f"perm:{email}:{company_id}"
        self.logger.info(f"[store_user_permissions] Cacheando permissões para {key}")
        try:
            ttl = int(getattr(settings, 'REDIS_PERM_TTL', 600))
            
            # 1. Copiamos o dicionário para não alterar a variável original por acidente
            cache_data = permissions.copy()
            
            # 2. Injetamos os campos obrigatórios exigidos pelo Pydantic
            cache_data["email"] = email
            cache_data["company_id"] = company_id
            cache_data["cached_at"] = datetime.utcnow().isoformat()
            
            # 3. Instanciamos o modelo (agora com todos os dados!)
            cache_obj = UserPermissionCache(**cache_data)
            
            await self.redis_client.setex(key, ttl, cache_obj.json())
            self.logger.info(f"[store_user_permissions] Permissões cacheadas com TTL {ttl}s.")
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
