import redis
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.models.session_models import SessionData, SessionStep
import logging
from backend.app.services.project_state_service import ProjectStateService
from fastapi import HTTPException

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

    def create_session(self, usuario_executor: str, projeto: str, analysis_type: str, comentario_usuario: Optional[str] = None, extracted_text: Optional[str] = None, project_id: Optional[str] = None, session_id: Optional[str] = None) -> str:
        if not session_id:
            raise ValueError("session_id é obrigatório para criar uma sessão.")
        created_at = datetime.utcnow().isoformat()
        if not project_id:
            project_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
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
            "reports": {}
        }
        self.redis_client.setex(f"session:{session_id}", self.session_ttl, self._serialize_session(session_data))
        return session_id

    def add_step(self, session_id: str, action: str, status: str, metadata: Optional[Dict[str, Any]] = None):
        key = f"session:{session_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Sessão {session_id} não encontrada no Redis.")
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

    def get_session(self, session_id: str) -> SessionData:
        key = f"session:{session_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Sessão {session_id} não encontrada no Redis.")
        session_dict = self._deserialize_session(session_json)
        steps = [SessionStep(**step) for step in session_dict.get("steps", [])]
        session_dict["steps"] = steps
        return SessionData(**session_dict)

    def update_session_status(self, session_id: str, status: str):
        key = f"session:{session_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Sessão {session_id} não encontrada no Redis.")
        session_data = self._deserialize_session(session_json)
        session_data["status"] = status
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))

    async def update_report(self, session_id: str, report_type: str, report_data: Any, analysis_type: Optional[str] = None, usuario_executor: Optional[str] = None, projeto: Optional[str] = None):
        self.logger.info(f"[update_report] Iniciando atualização de relatório para session_id={session_id}, report_type={report_type}")
        try:
            session_obj = await self._ensure_session_exists(session_id=session_id, usuario_executor=usuario_executor, projeto=projeto)
            self.logger.info(f"[update_report] Sessão garantida no Redis para session_id={session_id}")
        except Exception as e:
            self.logger.error(f"[update_report] Falha ao garantir sessão no Redis para session_id={session_id}: {e}")
            raise
        key = f"session:{session_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Sessão {session_id} não encontrada no Redis após tentativa de restauração.")
        session_data = self._deserialize_session(session_json)
        analysis_type_in_session = session_data.get("analysis_type")
        analysis_type = analysis_type or analysis_type_in_session
        report_field = None
        if hasattr(settings, "mcp_config_registry") and settings.mcp_config_registry and hasattr(settings.mcp_config_registry, "agents") and analysis_type in settings.mcp_config_registry.agents:
            agent_cfg = settings.mcp_config_registry.agents[analysis_type]
            if hasattr(agent_cfg, "report_mapping") and report_type in agent_cfg.report_mapping:
                report_field = agent_cfg.report_mapping[report_type]
        if not report_field:
            report_field = f"{report_type}_report"
        if "reports" not in session_data or not isinstance(session_data["reports"], dict):
            session_data["reports"] = {}
        reports_before = dict(session_data["reports"])
        self.logger.info(f"[update_report] Antes da atualização: session_id={session_id}, reports={json.dumps(reports_before, ensure_ascii=False)}")
        session_data["reports"][report_field] = report_data
        self.logger.info(f"[update_report] Chave modificada: '{report_field}' para session_id={session_id}")
        reports_after = dict(session_data["reports"])
        self.logger.info(f"[update_report] Após atualização: session_id={session_id}, reports={json.dumps(reports_after, ensure_ascii=False)}")
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))
        # Validação explícita: garantir que todas as chaves anteriores foram preservadas
        session_json_valid = self.redis_client.get(key)
        if not session_json_valid:
            self.logger.critical(f"[update_report] Sessão {session_id} não encontrada no Redis após atualização.")
            raise HTTPException(status_code=500, detail=f"Sessão {session_id} não encontrada no Redis após atualização.")
        session_data_valid = self._deserialize_session(session_json_valid)
        reports_dict = session_data_valid.get("reports", {})
        if not isinstance(reports_dict, dict):
            self.logger.critical(f"[update_report] Após update_report, reports não é um dicionário para session_id={session_id}")
            raise HTTPException(status_code=500, detail="Campo 'reports' corrompido após atualização.")
        missing_keys = [k for k in reports_before.keys() if k not in reports_dict]
        if missing_keys:
            self.logger.critical(f"[update_report] Após update_report, as chaves {missing_keys} não foram preservadas em reports para session_id={session_id}. Chaves atuais: {list(reports_dict.keys())}")
            raise HTTPException(status_code=500, detail=f"Chaves {missing_keys} não encontradas em reports após atualização.")
        if report_field not in reports_dict:
            self.logger.critical(f"[update_report] Após update_report, chave '{report_field}' não encontrada em reports para session_id={session_id}. Chaves atuais: {list(reports_dict.keys())}")
            raise HTTPException(status_code=500, detail=f"Chave '{report_field}' não encontrada em reports após atualização.")
        self.logger.info(f"[update_report] Validação pós-update_report: reports contém as chaves: {list(reports_dict.keys())}")
        try:
            session_obj = SessionData(**session_data)
            self.logger.info(f"[update_report] Salvando estado no Blob Storage imediatamente após atualização do relatório. session_id={session_id}, reports={json.dumps(session_data['reports'], ensure_ascii=False)}")
            await ProjectStateService.save_state_to_blob(session_obj)
            self.logger.info(f"[update_report] Estado salvo no Blob Storage para session_id={session_id}")
        except Exception as e:
            self.logger.error(f"Erro ao salvar estado imediatamente após update_report: {e}")

    async def _ensure_session_exists(self, session_id: str, usuario_executor: Optional[str] = None, projeto: Optional[str] = None) -> SessionData:
        self.logger.info(f"[_ensure_session_exists] Verificando existência da sessão no Redis para session_id={session_id}")
        try:
            session = self.get_session(session_id)
            self.logger.info(f"[_ensure_session_exists] Sessão encontrada no Redis para session_id={session_id}")
            return session
        except Exception as e:
            self.logger.warning(f"[_ensure_session_exists] Sessão não encontrada no Redis para session_id={session_id}: {e}")
        state = None
        if usuario_executor and projeto:
            self.logger.info(f"[_ensure_session_exists] Tentando carregar estado do Blob via usuario_executor={usuario_executor}, projeto={projeto}")
            try:
                state = await ProjectStateService.load_latest_state_from_blob(usuario_executor, projeto, session_id=session_id)
                if state:
                    self.logger.info(f"[_ensure_session_exists] Estado encontrado no Blob via usuario_executor/projeto para session_id={session_id}")
            except Exception as e:
                self.logger.warning(f"[_ensure_session_exists] Falha ao buscar estado no Blob via usuario_executor/projeto: {e}")
        if not state:
            self.logger.info(f"[_ensure_session_exists] Tentando carregar estado do Blob via session_id={session_id}")
            try:
                state = await ProjectStateService.load_latest_state_by_session_id(session_id)
                if state:
                    self.logger.info(f"[_ensure_session_exists] Estado encontrado no Blob via session_id={session_id}")
            except Exception as e:
                self.logger.warning(f"[_ensure_session_exists] Falha ao buscar estado no Blob via session_id: {e}")
        if state:
            usuario_executor_restore = state.get("usuario_executor")
            projeto_restore = state.get("projeto")
            analysis_type_restore = state.get("analysis_type")
            self.logger.info(f"[_ensure_session_exists] Restaurando sessão no Redis para session_id={session_id}, usuario_executor={usuario_executor_restore}, projeto={projeto_restore}, analysis_type={analysis_type_restore}")
            self.restore_session_from_state(
                usuario_executor_restore,
                projeto_restore,
                analysis_type_restore,
                state,
                session_id=session_id
            )
            session = self.get_session(session_id)
            self.logger.info(f"[_ensure_session_exists] Sessão restaurada no Redis para session_id={session_id}")
            return session
        self.logger.error(f"[_ensure_session_exists] Sessão não encontrada no Redis nem no Blob para session_id={session_id}")
        raise ValueError(f"Sessão {session_id} não encontrada no Redis nem no Blob Storage.")

    def restore_session_from_state(self, usuario_executor: str, projeto: str, analysis_type: str, project_state: Dict[str, Any], session_id: str) -> str:
        comentario_usuario = project_state.get("comentario_usuario")
        extracted_text = project_state.get("extracted_text")
        project_id = project_state.get("project_id")
        state_session_id = project_state.get("session_id")
        if state_session_id and session_id != state_session_id:
            self.logger.warning(f"[restore_session_from_state] Aviso: session_id fornecido ({session_id}) é diferente do session_id no estado ({state_session_id}). Usando o session_id do estado: {state_session_id}")
            session_id = state_session_id
        self.create_session(usuario_executor, projeto, analysis_type, comentario_usuario=comentario_usuario, extracted_text=extracted_text, project_id=project_id, session_id=session_id)
        key = f"session:{session_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Sessão {session_id} não encontrada no Redis.")
        session_data = self._deserialize_session(session_json)
        reports = project_state.get("reports", {})
        session_data["reports"] = reports
        session_data["last_saved_to_blob"] = project_state.get("last_saved_to_blob")
        session_data["docx_files"] = project_state.get("docx_files", [])
        session_data["comentario_usuario"] = comentario_usuario
        session_data["extracted_text"] = extracted_text
        session_data["project_id"] = project_id
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))
        return session_id

    def add_docx_file(self, session_id: str, blob_url: str):
        key = f"session:{session_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Sessão {session_id} não encontrada no Redis.")
        session_data = self._deserialize_session(session_json)
        if "docx_files" not in session_data or not isinstance(session_data["docx_files"], list):
            session_data["docx_files"] = []
        if blob_url not in session_data["docx_files"]:
            session_data["docx_files"].append(blob_url)
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))

    def update_session_extracted_text(self, session_id: str, extracted_text: str):
        key = f"session:{session_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Sessão {session_id} não encontrada no Redis.")
        session_data = self._deserialize_session(session_json)
        session_data["extracted_text"] = extracted_text
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))

    def update_session_on_state_change(self, session_id: str, updated_fields: Dict[str, Any]):
        from backend.app.services.background_state_saver import BackgroundStateSaver
        key = f"session:{session_id}"
        session_json = self.redis_client.get(key)
        if not session_json:
            raise ValueError(f"Sessão {session_id} não encontrada no Redis.")
        session_data = self._deserialize_session(session_json)
        session_data.update(updated_fields)
        session_data["last_modified"] = datetime.utcnow().isoformat()
        self.redis_client.setex(key, self.session_ttl, self._serialize_session(session_data))
        BackgroundStateSaver.schedule_periodic_save(session_id)

    def get_session_by_project(self, usuario_executor: str, projeto: str) -> Optional[SessionData]:
        self.logger.info(f"Buscando sessão por usuario_executor='{usuario_executor}', projeto='{projeto}'")
        try:
            for key in self.redis_client.scan_iter(match="session:*"):
                session_json = self.redis_client.get(key)
                if not session_json:
                    continue
                session_data = self._deserialize_session(session_json)
                if (
                    session_data.get("usuario_executor") == usuario_executor and
                    session_data.get("projeto") == projeto
                ):
                    self.logger.info(f"Encontrada sessão ativa para usuario_executor='{usuario_executor}', projeto='{projeto}', session_id='{session_data.get('session_id')}'")
                    return SessionData(**session_data)
        except Exception as e:
            self.logger.error(f"Erro ao buscar sessão por usuario_executor e projeto: {e}")
        return None
