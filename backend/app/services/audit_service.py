import json
import logging
from datetime import datetime
from backend.app.services.blob_storage_service import _get_blob_clients
from backend.app.models.audit_models import (
    FrontendToBackendPayload,
    BackendToFrontendPayload,
    MCPToBackendPayload,
    BackendToMCPPayload
)
import uuid

logger = logging.getLogger("AuditService")

class AuditService:
    @staticmethod
    def _generate_filename(prefix: str, project_id: str = None) -> str:
        now = datetime.utcnow().strftime("%Y%m%dT%H%M%S%fZ")
        unique_id = uuid.uuid4().hex[:8]
        if project_id:
            return f"{prefix}_{project_id}_{now}_{unique_id}.json"
        return f"{prefix}_{now}_{unique_id}.json"

    @staticmethod
    def upload_json_to_blob(json_data: dict, blob_folder: str, blob_filename: str) -> str:
        _, container_client = _get_blob_clients()
        blob_path = f"{blob_folder}/{blob_filename}"
        blob_client = container_client.get_blob_client(blob_path)
        blob_client.upload_blob(
            json.dumps(json_data, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
            overwrite=True,
            content_settings=None
        )
        logger.info(f"Payload de auditoria salvo em: {blob_client.url}")
        return blob_client.url

    @classmethod
    def save_frontend_to_backend_payload(cls, payload: dict, endpoint: str, method: str, usuario_executor: str = None, project_id: str = None):
        audit_payload = FrontendToBackendPayload(
            endpoint=endpoint,
            method=method,
            payload_data=payload,
            usuario_executor=usuario_executor,
            project_id=project_id
        )
        filename = cls._generate_filename("frontend_to_backend", project_id)
        folder = f"front_back_comunicacao/{usuario_executor or 'unknown'}"
        cls.upload_json_to_blob(audit_payload.dict(), folder, filename)

    @classmethod
    def save_backend_to_frontend_payload(cls, response: dict, endpoint: str, status_code: int, usuario_executor: str = None, project_id: str = None):
        audit_payload = BackendToFrontendPayload(
            endpoint=endpoint,
            status_code=status_code,
            response_data=response,
            usuario_executor=usuario_executor,
            project_id=project_id
        )
        filename = cls._generate_filename("backend_to_frontend", project_id)
        folder = f"front_back_comunicacao/{usuario_executor or 'unknown'}"
        cls.upload_json_to_blob(audit_payload.dict(), folder, filename)

    @classmethod
    def save_mcp_to_backend_payload(cls, payload: dict, webhook_type: str, project_id: str = None):
        audit_payload = MCPToBackendPayload(
            webhook_type=webhook_type,
            payload_data=payload,
            project_id=project_id
        )
        filename = cls._generate_filename("mcp_to_backend", project_id)
        folder = f"mcp_back_comunicacao/{project_id or 'unknown'}"
        cls.upload_json_to_blob(audit_payload.dict(), folder, filename)

    @classmethod
    def save_backend_to_mcp_payload(cls, payload: dict, analysis_type: str, project_id: str = None):
        audit_payload = BackendToMCPPayload(
            analysis_type=analysis_type,
            payload_data=payload,
            project_id=project_id
        )
        filename = cls._generate_filename("backend_to_mcp", project_id)
        folder = f"mcp_back_comunicacao/{project_id or 'unknown'}"
        cls.upload_json_to_blob(audit_payload.dict(), folder, filename)
