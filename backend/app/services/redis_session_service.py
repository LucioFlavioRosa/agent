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
        key = f"project:{project_id}"
        if self.redis_client.exists(key):
            self.logger.warning(f"Sessão já existe para project_id={project_id}. Não será criada nova sessão.")
            return project_id
        created_at = datetime.utcnow().isoformat()
        last_saved_to_blob = datetime.utcnow().isoformat()
        session_data = {
            "usuario_executor": usuario_executor,
            "nome_projeto": nome_projeto,
            "analysis_type": analysis_type,
            "created_at": created_at,
            "last_saved_to_blob": last_saved_to_blob,
            "docx_files": [],
            "project_id": project_id
        }
        report_fields = [
            "epicos_report",
            "features_report",
            "times_descricao_report",
            "alocacao_times_report",
            "premissas_riscos_report"
        ]
        if initial_state:
            for field in report_fields:
                if field in initial_state:
                    session_data[field] = initial_state[field]
                else:
                    session_data[field] = None
        else:
            for field in report_fields:
                session_data[field] = []
        if extracted_text is not None:
            session_data["extracted_text"] = extracted_text
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))
        return project_id

    def get_session_by_project_id(self, project_id: str) -> SessionData:
        key = f"project:{project_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Projeto {project_id} não encontrado no Redis.")
        session_dict = self._deserialize_session(session_json)
        return SessionData(**session_dict)

    def update_session_status(self, project_id: str, status: str):
        key = f"project:{project_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Projeto {project_id} não encontrado no Redis.")
        session_data = self._deserialize_session(session_json)
        session_data["status"] = status
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))

    async def _save_to_blob_after_update(self, project_id: str):
        try:
            session = self.get_session_by_project_id(project_id)
            await ProjectStateService.save_state_to_blob(session)
        except Exception as e:
            self.logger.error(f"Erro ao salvar estado no Blob após update_report para project_id={project_id}: {e}")

    def _update_single_field(self, project_id: str, field_name: str, field_value: Any):
        key = f"project:{project_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Projeto {project_id} não encontrado no Redis.")
        session_data = self._deserialize_session(session_json)
        session_data[field_name] = field_value
        session_data["last_modified"] = datetime.utcnow().isoformat()
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))

    def update_report(self, project_id: str, report_data: Dict[str, Any]):
        key = f"project:{project_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Projeto {project_id} não encontrado no Redis.")
        session_data = self._deserialize_session(session_json)
        if not isinstance(report_data, dict) or len(report_data) != 1:
            raise ValueError("report_data deve ser um dicionário com exatamente uma chave de relatório")
        valid_report_fields = [
            "epicos_report",
            "features_report",
            "times_descricao_report",
            "alocacao_times_report",
            "premissas_riscos_report"
        ]
        if len(list(report_data.keys())) > 1:
            raise ValueError(f"erro, deve haver apenas uma chave o report")
        report_field = list(report_data.keys())[0]
        if report_field not in valid_report_fields:
            raise ValueError(f"Chave de relatório '{report_field}' não é válida. Esperado uma das: {valid_report_fields}")
        # Não inicializar outros campos como listas vazias, apenas atualizar o campo informado
        valor_anterior = session_data.get(report_field)
        report_value = report_data[report_field]
        session_data[report_field] = report_value
        session_data["last_modified"] = datetime.utcnow().isoformat()
        self.logger.debug(f"Atualizando campo de relatório '{report_field}' para project_id={project_id}. Valor anterior: {valor_anterior} | Novo valor: {report_value}")
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))

    def restore_session_from_state(self, usuario_executor: str, nome_projeto: str, analysis_type: str, project_state: Dict[str, Any]) -> str:
        project_id = project_state.get("project_id")
        key = f"project:{project_id}"
        session_data = dict(project_state)
        session_data["usuario_executor"] = usuario_executor
        session_data["nome_projeto"] = nome_projeto
        session_data["analysis_type"] = analysis_type
        # Não sobrescrever campos de relatório existentes como listas vazias
        if not project_id:
            self.logger.error(f"[restore_session_from_state] Estado não contém project_id para nome_projeto='{nome_projeto}'.")
            raise ValueError(f"Estado do projeto não contém project_id para nome_projeto='{nome_projeto}'.")
        if "project_id" in session_data and session_data["project_id"] != project_id:
            self.logger.critical(f"[restore_session_from_state] Divergência de project_id detectada: project_id do estado='{session_data['project_id']}', esperado='{project_id}'.")
            raise ValueError(f"Divergência de project_id detectada ao restaurar sessão: estado='{session_data['project_id']}', esperado='{project_id}'")
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

    def update_session_on_state_change(self, project_id: str, updated_fields: Dict[str, Any]):
        key = f"project:{project_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Projeto {project_id} não encontrado no Redis.")
        session_data = self._deserialize_session(session_json)
        session_data.update(updated_fields)
        session_data["last_modified"] = datetime.utcnow().isoformat()
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))
