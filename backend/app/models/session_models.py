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
    epicos_report: Optional[Any] = Field(default=None)
    features_report: Optional[Any] = Field(default=None)
    times_descricao_report: Optional[Any] = Field(default=None)
    alocacao_times_report: Optional[Any] = Field(default=None)
    premissas_riscos_report: Optional[Any] = Field(default=None)
    last_saved_to_blob: Optional[datetime] = Field(default=None)
    docx_files: List[str] = Field(default_factory=list)
    comentario_usuario: Optional[str] = Field(default=None)
    extracted_text: Optional[str] = Field(default=None)
    project_id: Optional[str] = Field(default=None)

    def to_project_state(self) -> Dict[str, Any]:
        return {
            "usuario_executor": self.usuario_executor,
            "projeto": self.projeto,
            "analysis_type": self.analysis_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_saved_to_blob": self.last_saved_to_blob.isoformat() if self.last_saved_to_blob else None,
            "epicos_report": self.epicos_report,
            "features_report": self.features_report,
            "times_descricao_report": self.times_descricao_report,
            "alocacao_times_report": self.alocacao_times_report,
            "premissas_riscos_report": self.premissas_riscos_report,
            "docx_files": self.docx_files,
            "comentario_usuario": self.comentario_usuario,
            "extracted_text": self.extracted_text,
            "project_id": self.project_id
        }

    @classmethod
    def from_project_state(cls, state: Dict[str, Any]) -> "SessionData":
        return cls(
            session_id=state.get("session_id", ""),
            usuario_executor=state.get("usuario_executor", ""),
            projeto=state.get("projeto", ""),
            analysis_type=state.get("analysis_type", ""),
            created_at=datetime.fromisoformat(state["created_at"]) if state.get("created_at") else datetime.utcnow(),
            steps=[],
            epicos_report=state.get("epicos_report"),
            features_report=state.get("features_report"),
            times_descricao_report=state.get("times_descricao_report"),
            alocacao_times_report=state.get("alocacao_times_report"),
            premissas_riscos_report=state.get("premissas_riscos_report"),
            last_saved_to_blob=datetime.fromisoformat(state["last_saved_to_blob"]) if state.get("last_saved_to_blob") else None,
            docx_files=state.get("docx_files", []),
            comentario_usuario=state.get("comentario_usuario"),
            extracted_text=state.get("extracted_text"),
            project_id=state.get("project_id")
        )
