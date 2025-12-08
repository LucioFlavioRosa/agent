from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class SessionData(BaseModel):
    usuario_executor: str = Field(...)
    nome_projeto: str = Field(...)
    analysis_type: str = Field(...)
    created_at: datetime = Field(...)
    last_saved_to_blob: datetime = Field(...)
    docx_files: List[str] = Field(default_factory=list, description="Lista de URLs de todos os arquivos DOCX enviados pelo usuário")
    project_id: str = Field(...)
    epicos_report: Optional[Any] = Field(default=None)
    features_report: Optional[Any] = Field(default=None)
    times_descricao_report: Optional[Any] = Field(default=None)
    alocacao_times_report: Optional[Any] = Field(default=None)
    premissas_riscos_report: Optional[Any] = Field(default=None)

    def to_project_state(self) -> Dict[str, Any]:
        state = {
            "usuario_executor": self.usuario_executor,
            "nome_projeto": self.nome_projeto,
            "analysis_type": self.analysis_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_saved_to_blob": self.last_saved_to_blob.isoformat() if self.last_saved_to_blob else None,
            "docx_files": self.docx_files,
            "project_id": self.project_id,
            "epicos_report": self.epicos_report,
            "features_report": self.features_report,
            "times_descricao_report": self.times_descricao_report,
            "alocacao_times_report": self.alocacao_times_report,
            "premissas_riscos_report": self.premissas_riscos_report
        }
        state.pop("projeto", None)
        state.pop("comentario_usuario", None)
        state.pop("docx_blob_url", None)
        state.pop("extracted_text", None)
        return state

    @classmethod
    def from_project_state(cls, state: Dict[str, Any]) -> "SessionData":
        return cls(
            usuario_executor=state.get("usuario_executor", ""),
            nome_projeto=state.get("nome_projeto", ""),
            analysis_type=state.get("analysis_type", ""),
            created_at=datetime.fromisoformat(state["created_at"]) if state.get("created_at") else datetime.utcnow(),
            last_saved_to_blob=datetime.fromisoformat(state["last_saved_to_blob"]) if state.get("last_saved_to_blob") else datetime.utcnow(),
            docx_files=state.get("docx_files", []),
            project_id=state.get("project_id"),
            epicos_report=state.get("epicos_report"),
            features_report=state.get("features_report"),
            times_descricao_report=state.get("times_descricao_report"),
            alocacao_times_report=state.get("alocacao_times_report"),
            premissas_riscos_report=state.get("premissas_riscos_report")
        )
