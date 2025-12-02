import redis
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.models.session_models import SessionData, SessionStep

REPORT_TYPES = {
    'epicos': 'epicos_report',
    'features': 'features_report',
    'times_descricao': 'times_descricao_report',
    'alocacao_times': 'alocacao_times_report',
    'premissas_riscos': 'premissas_riscos_report'
}

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

    def create_session(self, usuario_executor: str, projeto: str, analysis_type: str, comentario_usuario: Optional[str] = None) -> str:
        session_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        session_data = {
            "session_id": session_id,
            "usuario_executor": usuario_executor,
            "projeto": projeto,
            "analysis_type": analysis_type,
            "created_at": created_at,
            "steps": [],
            "epicos_report": None,
            "features_report": None,
            "times_descricao_report": None,
            "alocacao_times_report": None,
            "premissas_riscos_report": None,
            "last_saved_to_blob": None,
            "docx_files": [],
            "comentario_usuario": comentario_usuario
        }
        self.redis_client.setex(f"session:{session_id}", self.session_ttl, json.dumps(session_data))
        return session_id

    def add_step(self, session_id: str, action: str, status: str, metadata: Optional[Dict[str, Any]] = None):
        key = f"session:{session_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Sessão {session_id} não encontrada no Redis.")
        session_data = json.loads(session_json)
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
        self.redis_client.setex(key, self.session_ttl, json.dumps(session_data))

    def get_session(self, session_id: str) -> SessionData:
        key = f"session:{session_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Sessão {session_id} não encontrada no Redis.")
        session_dict = json.loads(session_json)
        steps = [SessionStep(**step) for step in session_dict.get("steps", [])]
        session_dict["steps"] = steps
        return SessionData(**session_dict)

    def update_session_status(self, session_id: str, status: str):
        key = f"session:{session_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Sessão {session_id} não encontrada no Redis.")
        session_data = json.loads(session_json)
        session_data["status"] = status
        self.redis_client.setex(key, self.session_ttl, json.dumps(session_data))

    def update_report(self, session_id: str, report_type: str, report_data: Any):
        if report_type not in REPORT_TYPES:
            raise ValueError(f"Tipo de relatório inválido: {report_type}")
        key = f"session:{session_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Sessão {session_id} não encontrada no Redis.")
        session_data = json.loads(session_json)
        session_data[REPORT_TYPES[report_type]] = report_data
        self.redis_client.setex(key, self.session_ttl, json.dumps(session_data))

    def restore_session_from_state(self, usuario_executor: str, projeto: str, analysis_type: str, project_state: Dict[str, Any]) -> str:
        comentario_usuario = project_state.get("comentario_usuario")
        session_id = self.create_session(usuario_executor, projeto, analysis_type, comentario_usuario=comentario_usuario)
        key = f"session:{session_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Sessão {session_id} não encontrada no Redis.")
        session_data = json.loads(session_json)
        session_data["epicos_report"] = project_state.get("epicos_report")
        session_data["features_report"] = project_state.get("features_report")
        session_data["times_descricao_report"] = project_state.get("times_descricao_report")
        session_data["alocacao_times_report"] = project_state.get("alocacao_times_report")
        session_data["premissas_riscos_report"] = project_state.get("premissas_riscos_report")
        session_data["last_saved_to_blob"] = project_state.get("last_saved_to_blob")
        session_data["docx_files"] = project_state.get("docx_files", [])
        session_data["comentario_usuario"] = comentario_usuario
        self.redis_client.setex(key, self.session_ttl, json.dumps(session_data))
        return session_id

    def add_docx_file(self, session_id: str, blob_url: str):
        key = f"session:{session_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Sessão {session_id} não encontrada no Redis.")
        session_data = json.loads(session_json)
        if "docx_files" not in session_data or not isinstance(session_data["docx_files"], list):
            session_data["docx_files"] = []
        if blob_url not in session_data["docx_files"]:
            session_data["docx_files"].append(blob_url)
        self.redis_client.setex(key, self.session_ttl, json.dumps(session_data))
