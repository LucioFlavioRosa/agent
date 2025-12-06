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
    usuario_executor: str = Field(...)
    projeto: str = Field(...)
    analysis_type: str = Field(...)
    created_at: datetime = Field(...)
    steps: List[SessionStep] = Field(default_factory=list)
    last_saved_to_blob: Optional[datetime] = Field(default=None)
    docx_files: List[str] = Field(default_factory=list)
    comentario_usuario: Optional[str] = Field(default=None)
    extracted_text: Optional[str] = Field(default=None)
    project_id: str = Field(...)
    epicos_report: Optional[Any] = Field(default=None)
    features_report: Optional[Any] = Field(default=None)
    times_descricao_report: Optional[Any] = Field(default=None)
    alocacao_times_report: Optional[Any] = Field(default=None)
    premissas_riscos_report: Optional[Any] = Field(default=None)
    docx_blob_url: Optional[str] = Field(default=None)

    def to_project_state(self) -> Dict[str, Any]:
        return {
            "usuario_executor": self.usuario_executor,
            "projeto": self.projeto,
            "nome_projeto": self.projeto,
            "analysis_type": self.analysis_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_saved_to_blob": self.last_saved_to_blob.isoformat() if self.last_saved_to_blob else None,
            "docx_files": self.docx_files,
            "comentario_usuario": self.comentario_usuario,
            "extracted_text": self.extracted_text,
            "project_id": self.project_id,
            "docx_blob_url": self.docx_blob_url,
            "epicos_report": self.epicos_report if self.epicos_report is not None else [],
            "features_report": self.features_report if self.features_report is not None else [],
            "times_descricao_report": self.times_descricao_report if self.times_descricao_report is not None else [],
            "alocacao_times_report": self.alocacao_times_report if self.alocacao_times_report is not None else [],
            "premissas_riscos_report": self.premissas_riscos_report if self.premissas_riscos_report is not None else []
        }

    @classmethod
    def from_project_state(cls, state: Dict[str, Any]) -> "SessionData":
        legacy_reports = state.get("reports", {})
        def get_report_field(field):
            if field in state and state[field] is not None:
                return state[field]
            if legacy_reports and field in legacy_reports and legacy_reports[field] is not None:
                return legacy_reports[field]
            return []
        return cls(
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
            epicos_report=get_report_field("epicos_report"),
            features_report=get_report_field("features_report"),
            times_descricao_report=get_report_field("times_descricao_report"),
            alocacao_times_report=get_report_field("alocacao_times_report"),
            premissas_riscos_report=get_report_field("premissas_riscos_report"),
            docx_blob_url=state.get("docx_blob_url")
        )
