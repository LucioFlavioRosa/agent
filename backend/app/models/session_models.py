from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class SessionStep(BaseModel):
    step_id: str = Field(...)
    timestamp: datetime = Field(...)
    action: str = Field(...)
    status: str = Field(...)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class SessionData(BaseModel):
    session_id: str = Field(...)
    usuario_executor: str = Field(...)
    projeto: str = Field(...)
    analysis_type: str = Field(...)
    created_at: datetime = Field(...)
    steps: List[SessionStep] = Field(default_factory=list)
    last_saved_to_blob: Optional[datetime] = Field(default=None)
    docx_files: List[str] = Field(default_factory=list)
    comentario_usuario: Optional[str] = Field(default=None)
    extracted_text: Optional[str] = Field(default=None)
    project_id: Optional[str] = Field(default=None)
    reports: Dict[str, Any] = Field(default_factory=dict)
    last_mcp_job_id: Optional[str] = Field(default=None)

    def to_project_state(self) -> Dict[str, Any]:
        return {
            "usuario_executor": self.usuario_executor,
            "projeto": self.projeto,
            "analysis_type": self.analysis_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_saved_to_blob": self.last_saved_to_blob.isoformat() if self.last_saved_to_blob else None,
            "docx_files": self.docx_files,
            "comentario_usuario": self.comentario_usuario,
            "extracted_text": self.extracted_text,
            "project_id": self.project_id,
            "reports": self.reports,
            "last_mcp_job_id": self.last_mcp_job_id
        }

    @classmethod
    def from_project_state(cls, state: Dict[str, Any]) -> "SessionData":
        reports = state.get("reports", {})
        migrated_reports = dict(reports) if reports else {}
        legacy_fields = [
            "epicos_report", "features_report", "times_descricao_report", "alocacao_times_report", "premissas_riscos_report"
        ]
        for field in legacy_fields:
            if field in state and state[field] is not None:
                migrated_reports[field] = state[field]
        return cls(
            session_id=state.get("session_id", ""),
            usuario_executor=state.get("usuario_executor", ""),
            projeto=state.get("projeto", ""),
            analysis_type=state.get("analysis_type", ""),
            created_at=datetime.fromisoformat(state["created_at"]) if state.get("created_at") else datetime.utcnow(),
            steps=[],
            last_saved_to_blob=datetime.fromisoformat(state["last_saved_to_blob"]) if state.get("last_saved_to_blob") else None,
            docx_files=state.get("docx_files", []),
            comentario_usuario=state.get("comentario_usuario"),
            extracted_text=state.get("extracted_text"),
            project_id=state.get("project_id"),
            reports=migrated_reports,
            last_mcp_job_id=state.get("last_mcp_job_id")
        )
