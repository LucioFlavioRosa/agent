import redis
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.models.session_models import SessionData
import logging
import asyncio
from backend.app.services.project_state_service import ProjectStateService

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

    def create_session(self, usuario_executor: str, nome_projeto: str, analysis_type: str, project_id: str, extracted_text: Optional[str] = None, initial_state: Optional[Dict[str, Any]] = None) -> str:
        if not usuario_executor or not isinstance(usuario_executor, str) or not usuario_executor.strip():
            blob_state = None
            try:
                blob_state = asyncio.run(ProjectStateService.load_latest_state_from_blob(
                    usuario_executor or "",
                    project_id=project_id,
                    nome_projeto=nome_projeto
                ))
            except Exception as e:
                self.logger.error(f"Erro ao buscar estado do Blob Storage para preencher usuario_executor: {str(e)}")
            if blob_state:
                usuario_executor = blob_state.get("usuario_executor")
            if not usuario_executor or not isinstance(usuario_executor, str) or not usuario_executor.strip():
                raise ValueError("Campo obrigatorio ausente: usuario_executor")
        if not nome_projeto or not isinstance(nome_projeto, str) or not nome_projeto.strip():
            blob_state = None
            try:
                blob_state = asyncio.run(ProjectStateService.load_latest_state_from_blob(
                    usuario_executor or "",
                    project_id=project_id,
                    nome_projeto=nome_projeto
                ))
            except Exception as e:
                self.logger.error(f"Erro ao buscar estado do Blob Storage para preencher nome_projeto: {str(e)}")
            if blob_state:
                nome_projeto = blob_state.get("nome_projeto")
            if not nome_projeto or not isinstance(nome_projeto, str) or not nome_projeto.strip():
                raise ValueError("Campo obrigatorio ausente: nome_projeto")
        if not project_id or not isinstance(project_id, str) or not project_id.strip():
            blob_state = None
            try:
                blob_state = asyncio.run(ProjectStateService.load_latest_state_from_blob(
                    usuario_executor or "",
                    project_id=project_id,
                    nome_projeto=nome_projeto
                ))
            except Exception as e:
                self.logger.error(f"Erro ao buscar estado do Blob Storage para preencher project_id: {str(e)}")
            if blob_state:
                project_id = blob_state.get("project_id")
            if not project_id or not isinstance(project_id, str) or not project_id.strip():
                raise ValueError("Campo obrigatorio ausente: project_id")
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
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))
        return project_id

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
        if not nome_projeto_val or not isinstance(nome_projeto_val, str) or not nome_projeto_val.strip():
            blob_state = None
            try:
                blob_state = asyncio.run(ProjectStateService.load_latest_state_from_blob(
                    usuario_executor or "",
                    project_id=project_id,
                    nome_projeto=nome_projeto
                ))
            except Exception as e:
                self.logger.error(f"Erro ao buscar estado do Blob Storage para preencher campos obrigatórios: {str(e)}")
            if blob_state:
                nome_projeto_val = blob_state.get("nome_projeto")
        if not usuario_executor_val or not isinstance(usuario_executor_val, str) or not usuario_executor_val.strip():
            blob_state = None
            try:
                blob_state = asyncio.run(ProjectStateService.load_latest_state_from_blob(
                    usuario_executor or "",
                    project_id=project_id,
                    nome_projeto=nome_projeto
                ))
            except Exception as e:
                self.logger.error(f"Erro ao buscar estado do Blob Storage para preencher campos obrigatórios: {str(e)}")
            if blob_state:
                usuario_executor_val = blob_state.get("usuario_executor")
        if not project_id or not isinstance(project_id, str) or not project_id.strip():
            blob_state = None
            try:
                blob_state = asyncio.run(ProjectStateService.load_latest_state_from_blob(
                    usuario_executor or "",
                    project_id=project_id,
                    nome_projeto=nome_projeto
                ))
            except Exception as e:
                self.logger.error(f"Erro ao buscar estado do Blob Storage para preencher campos obrigatórios: {str(e)}")
            if blob_state:
                project_id = blob_state.get("project_id")
        if not nome_projeto_val or not usuario_executor_val or not project_id:
            raise ValueError("Campos obrigatórios ausentes ao restaurar sessão: usuario_executor, nome_projeto, project_id")
        key = f"project:{project_id}:resumo"
        session_data = dict(project_state)
        session_data["usuario_executor"] = usuario_executor_val
        session_data["nome_projeto"] = nome_projeto_val
        session_data["analysis_type"] = analysis_type
        session_data["ultima_analysis_type"] = analysis_type
        session_data["ultima_atualizacao"] = datetime.utcnow().isoformat()
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))
        return project_id
