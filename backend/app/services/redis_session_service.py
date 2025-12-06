import redis
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.models.session_models import SessionData, SessionStep
import logging

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

    def create_session(self, usuario_executor: str, projeto: str, analysis_type: str, project_id: str, comentario_usuario: Optional[str] = None, extracted_text: Optional[str] = None) -> str:
        created_at = datetime.utcnow().isoformat()
        session_data = {
            "usuario_executor": usuario_executor,
            "projeto": projeto,
            "analysis_type": analysis_type,
            "created_at": created_at,
            "steps": [],
            "last_saved_to_blob": None,
            "docx_files": [],
            "comentario_usuario": comentario_usuario,
            "extracted_text": extracted_text,
            "project_id": project_id,
            "nome_projeto": projeto,
            "reports": {}
        }
        self.redis_client.setex(f"project:{project_id}", self.session_ttl, self._serialize_session(session_data))
        return project_id

    def add_step(self, project_id: str, action: str, status: str, metadata: Optional[Dict[str, Any]] = None):
        key = f"project:{project_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Projeto {project_id} não encontrado no Redis.")
        session_data = self._deserialize_session(session_json)
        step_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        step = {
            "step_id": step_id,
            "timestamp": timestamp,
            "action": action,
            "status": status,
            "metadata": metadata or {}
        }
        session_data["steps"].append(step)
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))

    def get_session_by_project_id(self, project_id: str) -> SessionData:
        key = f"project:{project_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Projeto {project_id} não encontrado no Redis.")
        session_dict = self._deserialize_session(session_json)
        steps = [SessionStep(**step) for step in session_dict.get("steps", [])]
        session_dict["steps"] = steps
        return SessionData(**session_dict)

    def update_session_status(self, project_id: str, status: str):
        key = f"project:{project_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Projeto {project_id} não encontrado no Redis.")
        session_data = self._deserialize_session(session_json)
        session_data["status"] = status
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))

    def update_report(self, project_id: str, report_data: Dict[str, Any]):
        key = f"project:{project_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Projeto {project_id} não encontrado no Redis.")
        session_data = self._deserialize_session(session_json)
        if not isinstance(report_data, dict) or len(report_data) != 1:
            raise ValueError("report_data deve ser um dicionário com exatamente uma chave de relatório")
        for report_field, value in report_data.items():
            session_data[report_field] = value
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))

    def restore_session_from_state(self, usuario_executor: str, projeto: str, analysis_type: str, project_state: Dict[str, Any]) -> str:
        comentario_usuario = project_state.get("comentario_usuario")
        extracted_text = project_state.get("extracted_text")
        project_id = project_state.get("project_id")
        nome_projeto = project_state.get("nome_projeto") or project_state.get("projeto") or projeto
        self.create_session(usuario_executor, nome_projeto, analysis_type, project_id=project_id, comentario_usuario=comentario_usuario, extracted_text=extracted_text)
        key = f"project:{project_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Projeto {project_id} não encontrado no Redis.")
        session_data = self._deserialize_session(session_json)
        reports = {}
        if "reports" in project_state and isinstance(project_state["reports"], dict):
            reports.update(project_state["reports"])
        legacy_fields = [
            "epicos_report", "features_report", "times_descricao_report", "alocacao_times_report", "premissas_riscos_report"
        ]
        for field in legacy_fields:
            if field in project_state and project_state[field] is not None:
                reports[field] = project_state[field]
        session_data["reports"] = reports
        session_data["last_saved_to_blob"] = project_state.get("last_saved_to_blob")
        session_data["docx_files"] = project_state.get("docx_files", [])
        session_data["comentario_usuario"] = comentario_usuario
        session_data["extracted_text"] = extracted_text
        session_data["project_id"] = project_id
        session_data["nome_projeto"] = nome_projeto
        session_data["projeto"] = nome_projeto
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))
        return project_id

    def add_docx_file(self, project_id: str, blob_url: str):
        key = f"project:{project_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Projeto {project_id} não encontrado no Redis.")
        session_data = self._deserialize_session(session_json)
        if "docx_files" not in session_data or not isinstance(session_data["docx_files"], list):
            session_data["docx_files"] = []
        if blob_url not in session_data["docx_files"]:
            session_data["docx_files"].append(blob_url)
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))

    def update_session_extracted_text(self, project_id: str, extracted_text: str):
        key = f"project:{project_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Projeto {project_id} não encontrado no Redis.")
        session_data = self._deserialize_session(session_json)
        session_data["extracted_text"] = extracted_text
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))

    def update_session_on_state_change(self, project_id: str, updated_fields: Dict[str, Any]):
        from backend.app.services.background_state_saver import BackgroundStateSaver
        key = f"project:{project_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Projeto {project_id} não encontrado no Redis.")
        session_data = self._deserialize_session(session_json)
        session_data.update(updated_fields)
        session_data["last_modified"] = datetime.utcnow().isoformat()
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))
        BackgroundStateSaver.schedule_periodic_save(project_id)
