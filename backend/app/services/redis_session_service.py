import redis
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.models.session_models import SessionData, SessionStep

class RedisSessionService:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=getattr(settings, 'REDIS_HOST', 'localhost'),
            port=int(getattr(settings, 'REDIS_PORT', 6379)),
            password=getattr(settings, 'REDIS_PASSWORD', None),
            db=int(getattr(settings, 'REDIS_DB', 0)),
            decode_responses=True
        )
        self.session_ttl = int(getattr(settings, 'REDIS_SESSION_TTL', 86400))

    def create_session(self, usuario_executor: str, projeto: str, analysis_name: str, analysis_type: str) -> str:
        session_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        session_data = {
            "session_id": session_id,
            "usuario_executor": usuario_executor,
            "projeto": projeto,
            "analysis_name": analysis_name,
            "analysis_type": analysis_type,
            "created_at": created_at,
            "steps": []
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
