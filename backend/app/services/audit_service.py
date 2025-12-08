import logging
import json
from datetime import datetime
from backend.app.services.blob_storage_service import _get_blob_clients, upload_json_to_blob
from backend.app.models.audit_models import (
    FrontendToBackendPayload,
    BackendToFrontendPayload,
    MCPToBackendPayload,
    BackendToMCPPayload
)
import uuid
from backend.app.utils.json_encoder import safe_json_dumps

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
        from backend.app.services.blob_storage_service import upload_json_to_blob
        return upload_json_to_blob(json_data, blob_folder, blob_filename)

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
        audit_dict = audit_payload.dict()
        json_str = safe_json_dumps(audit_dict)
        cls.upload_json_to_blob(json.loads(json_str), folder, filename)

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
        audit_dict = audit_payload.dict()
        json_str = safe_json_dumps(audit_dict)
        cls.upload_json_to_blob(json.loads(json_str), folder, filename)

    @classmethod
    def save_mcp_to_backend_payload(cls, payload: dict, webhook_type: str, project_id: str = None):
        audit_payload = MCPToBackendPayload(
            webhook_type=webhook_type,
            payload_data=payload,
            project_id=project_id
        )
        filename = cls._generate_filename("mcp_to_backend", project_id)
        folder = f"mcp_back_comunicacao/{project_id or 'unknown'}"
        audit_dict = audit_payload.dict()
        json_str = safe_json_dumps(audit_dict)
        cls.upload_json_to_blob(json.loads(json_str), folder, filename)

    @classmethod
    def save_backend_to_mcp_payload(cls, payload: dict, analysis_type: str, project_id: str = None):
        audit_payload = BackendToMCPPayload(
            analysis_type=analysis_type,
            payload_data=payload,
            project_id=project_id
        )
        filename = cls._generate_filename("backend_to_mcp", project_id)
        folder = f"mcp_back_comunicacao/{project_id or 'unknown'}"
        audit_dict = audit_payload.dict()
        json_str = safe_json_dumps(audit_dict)
        cls.upload_json_to_blob(json.loads(json_str), folder, filename)
