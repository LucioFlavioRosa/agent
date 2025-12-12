import redis
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from backend.app.core.config import settings
from backend.app.models.session_models import SessionData
import logging
import asyncio
from backend.app.services.project_state_service import ProjectStateService
from backend.app.models.job_models import JobData

def ensure_project_id(session_data: dict, usuario_executor: str = None, nome_projeto: str = None) -> str:
    project_id = session_data.get("project_id")
    if project_id and isinstance(project_id, str) and project_id.strip():
        return project_id
    try:
        estado_blob = None
        if usuario_executor and nome_projeto:
            try:
                estado_blob = asyncio.run(ProjectStateService.load_latest_state_from_blob(usuario_executor, nome_projeto=nome_projeto))
            except Exception as e:
                logging.getLogger("RedisSessionService").error(f"Erro ao buscar estado do Blob Storage para preencher project_id: {str(e)}")
        if estado_blob and estado_blob.get("project_id"):
            session_data["project_id"] = estado_blob["project_id"]
            return estado_blob["project_id"]
    except Exception as e:
        logging.getLogger("RedisSessionService").error(f"Erro inesperado ao tentar garantir project_id: {str(e)}")
    novo_id = str(uuid.uuid4())
    session_data["project_id"] = novo_id
    logging.getLogger("RedisSessionService").critical(f"project_id ausente, gerado novo UUID: {novo_id}")
    return novo_id

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
        data = self.get_resumo_state(project_id)
        if data:
            try:
                return SessionData(**data)
            except Exception as e:
                self.logger.error(f"Erro ao converter dados do Redis para SessionData: {e}")
                return None
        return None

    def update_report(self, project_id: str, report_data: Dict[str, Any]):
        key = f"project:{project_id}:resumo"
        session_json = self.redis_client.get(key)
        if session_json:
            try:
                session_data = self._deserialize_session(session_json)
                session_data.update(report_data)
                session_data["ultima_atualizacao"] = datetime.utcnow().isoformat()
                self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))
                self.logger.info(f"Relatório merged e atualizado no Redis para projeto {project_id}")
            except Exception as e:
                self.logger.error(f"Erro ao atualizar report no Redis: {e}")
                raise e
        else:
            msg = f"Tentativa de atualizar report para sessão inexistente no Redis: {project_id}"
            self.logger.error(msg)

    def create_session(self, usuario_executor: str, nome_projeto: str, analysis_type: str, project_id: str, extracted_text: Optional[str] = None, initial_state: Optional[Dict[str, Any]] = None) -> str:
        blob_state_cached = None
        def get_blob_state_once():
            nonlocal blob_state_cached
            if blob_state_cached is None:
                try:
                    blob_state_cached = asyncio.run(ProjectStateService.load_latest_state_from_blob(
                        usuario_executor or "",
                        project_id=project_id,
                        nome_projeto=nome_projeto
                    )) or {}
                except Exception as e:
                    self.logger.error(f"Erro ao buscar estado do Blob Storage: {str(e)}")
                    blob_state_cached = {}
            return blob_state_cached
        if not usuario_executor or not isinstance(usuario_executor, str) or not usuario_executor.strip():
            state = get_blob_state_once()
            usuario_executor = state.get("usuario_executor")
            if not usuario_executor or not isinstance(usuario_executor, str) or not usuario_executor.strip():
                raise ValueError("Campo obrigatorio ausente: usuario_executor")
        if not nome_projeto or not isinstance(nome_projeto, str) or not nome_projeto.strip():
            state = get_blob_state_once()
            nome_projeto = state.get("nome_projeto")
            if not nome_projeto or not isinstance(nome_projeto, str) or not nome_projeto.strip():
                raise ValueError("Campo obrigatorio ausente: nome_projeto")
        if not project_id or not isinstance(project_id, str) or not project_id.strip():
            session_data_temp = initial_state if initial_state else {}
            session_data_temp["usuario_executor"] = usuario_executor
            session_data_temp["nome_projeto"] = nome_projeto
            project_id = ensure_project_id(session_data_temp, usuario_executor, nome_projeto)
        key = f"project:{project_id}:resumo"
        created_at = datetime.utcnow().isoformat()
        last_saved_to_blob = datetime.utcnow().isoformat()
        session_data = {
            "usuario_executor": usuario_executor,
            "nome_projeto": nome_projeto,
            "analysis_type": analysis_type,
            "created_at": created_at,
            "last_saved_to_blob": last_saved_to_blob,
            "project_id": project_id,
            "ultima_analysis_type": analysis_type,
            "ultima_atualizacao": last_saved_to_blob
        }
        if extracted_text:
             session_data["extracted_text"] = extracted_text
        if initial_state:
            session_data.update(initial_state)
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))
        return project_id

    def add_docx_file(self, project_id: str, blob_url: str):
        key = f"project:{project_id}:resumo"
        session_json = self.redis_client.get(key)
        if session_json:
            try:
                session_data = self._deserialize_session(session_json)
                session_data["docx_url"] = blob_url
                session_data["ultima_atualizacao"] = datetime.utcnow().isoformat()
                self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))
                self.logger.info(f"DOCX vinculado com sucesso ao projeto {project_id}")
            except Exception as e:
                self.logger.error(f"Erro ao atualizar sessão com DOCX no Redis: {e}")
        else:
            self.logger.warning(f"Tentativa de adicionar DOCX a uma sessão inexistente: {project_id}")

    def create_report_state(self, project_id: str, report_type: str, state_data: Dict[str, Any]):
        key = f"project:{project_id}:report:{report_type}"
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(state_data))

    def update_report_state(self, project_id: str, report_type: str, state_data: Dict[str, Any]):
        key = f"project:{project_id}:report:{report_type}"
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(state_data))

    def get_report_state(self, project_id: str, report_type: str) -> Optional[Dict[str, Any]]:
        key = f"project:{project_id}:report:{report_type}"
        session_json = self.redis_client.get(key)
        if session_json:
            return self._deserialize_session(session_json)
        return None

    def get_resumo_state(self, project_id: str) -> Optional[Dict[str, Any]]:
        key = f"project:{project_id}:resumo"
        session_json = self.redis_client.get(key)
        if session_json:
            self.logger.info(f"Resumo do projeto {project_id} encontrado no Redis.")
            return self._deserialize_session(session_json)
        self.logger.info(f"Resumo do projeto {project_id} não encontrado no Redis.")
        return None

    def restore_session_from_state(self, usuario_executor: str, nome_projeto: str, analysis_type: str, project_state: Dict[str, Any]) -> str:
        project_id = project_state.get("project_id")
        nome_projeto_val = project_state.get("nome_projeto")
        usuario_executor_val = project_state.get("usuario_executor")
        if not project_id or not isinstance(project_id, str) or not project_id.strip():
            session_data = dict(project_state)
            session_data["usuario_executor"] = usuario_executor or usuario_executor_val
            session_data["nome_projeto"] = nome_projeto or nome_projeto_val
            pid = ensure_project_id(session_data, session_data["usuario_executor"], session_data["nome_projeto"])
            project_id = pid
        if (not nome_projeto_val) or (not usuario_executor_val):
             try:
                blob_state = asyncio.run(ProjectStateService.load_latest_state_from_blob(
                    usuario_executor or "",
                    project_id=project_id,
                    nome_projeto=nome_projeto
                ))
                if blob_state:
                    nome_projeto_val = nome_projeto_val or blob_state.get("nome_projeto")
                    usuario_executor_val = usuario_executor_val or blob_state.get("usuario_executor")
             except Exception as e:
                self.logger.error(f"Erro ao buscar estado do Blob Storage para preencher campos: {str(e)}")
        if not nome_projeto_val or not usuario_executor_val or not project_id:
            raise ValueError("Campos obrigatórios ausentes ao restaurar sessão: usuario_executor, nome_projeto, project_id")
        key = f"project:{project_id}:resumo"
        session_data = dict(project_state)
        session_data["usuario_executor"] = usuario_executor_val
        session_data["nome_projeto"] = nome_projeto_val
        session_data["analysis_type"] = analysis_type
        session_data["ultima_analysis_type"] = analysis_type
        session_data["ultima_atualizacao"] = datetime.utcnow().isoformat()
        session_data["project_id"] = project_id
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
                # Preencher completed_at SOMENTE na primeira transição para 'done'
                if not data.get('completed_at'):
                    data['completed_at'] = now_iso
            self.redis_client.setex(key, self.session_ttl, json.dumps(data))
        except Exception as e:
            self.logger.error(f"Erro ao atualizar status do job {job_id}: {e}")

    def get_active_job_for_project(self, project_id: str) -> Optional[JobData]:
        pattern = f"job:*"
        job_keys = self.redis_client.keys(pattern)
        jobs: List[JobData] = []
        for key in job_keys:
            job_json = self.redis_client.get(key)
            if not job_json:
                continue
            try:
                data = json.loads(job_json)
                if data.get('project_id') == project_id and data.get('status') in ('pending', 'in_progress'):
                    jobs.append(JobData(**data))
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
        # Ordena por completed_at (se existir), senão por response_timestamp, senão datetime.min
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
