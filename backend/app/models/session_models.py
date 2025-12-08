from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

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
        logger = logging.getLogger("SessionData")
        state = {
            "usuario_executor": self.usuario_executor,
            "nome_projeto": self.nome_projeto,
            "analysis_type": self.analysis_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_saved_to_blob": self.last_saved_to_blob.isoformat() if self.last_saved_to_blob else None,
            "docx_files": self.docx_files,
            "project_id": self.project_id,
            "epicos_report": self.epicos_report if isinstance(self.epicos_report, list) else ([] if self.epicos_report is None else list(self.epicos_report) if hasattr(self.epicos_report, '__iter__') and not isinstance(self.epicos_report, str) else [self.epicos_report]),
            "features_report": self.features_report if isinstance(self.features_report, list) else ([] if self.features_report is None else list(self.features_report) if hasattr(self.features_report, '__iter__') and not isinstance(self.features_report, str) else [self.features_report]),
            "times_descricao_report": self.times_descricao_report if isinstance(self.times_descricao_report, list) else ([] if self.times_descricao_report is None else list(self.times_descricao_report) if hasattr(self.times_descricao_report, '__iter__') and not isinstance(self.times_descricao_report, str) else [self.times_descricao_report]),
            "alocacao_times_report": self.alocacao_times_report if isinstance(self.alocacao_times_report, list) else ([] if self.alocacao_times_report is None else list(self.alocacao_times_report) if hasattr(self.alocacao_times_report, '__iter__') and not isinstance(self.alocacao_times_report, str) else [self.alocacao_times_report]),
            "premissas_riscos_report": self.premissas_riscos_report if isinstance(self.premissas_riscos_report, list) else ([] if self.premissas_riscos_report is None else list(self.premissas_riscos_report) if hasattr(self.premissas_riscos_report, '__iter__') and not isinstance(self.premissas_riscos_report, str) else [self.premissas_riscos_report])
        }
        normalized_count = 0
        for field in [
            "epicos_report",
            "features_report",
            "times_descricao_report",
            "alocacao_times_report",
            "premissas_riscos_report"
        ]:
            if state[field] is None or not isinstance(state[field], list):
                state[field] = []
                normalized_count += 1
        if normalized_count > 0:
            logger.debug(f"Normalização: {normalized_count} campos de relatório convertidos para lista em to_project_state().")
        state.pop("projeto", None)
        state.pop("comentario_usuario", None)
        state.pop("docx_blob_url", None)
        state.pop("extracted_text", None)
        return state

    @classmethod
    def from_project_state(cls, state: Dict[str, Any]) -> "SessionData":
        logger = logging.getLogger("SessionData")
        normalized_fields = 0
        def _normalize(field):
            nonlocal normalized_fields
            v = state.get(field)
            if v is None or not isinstance(v, list):
                normalized_fields += 1
                return []
            return v
        return cls(
            usuario_executor=state.get("usuario_executor", ""),
            nome_projeto=state.get("nome_projeto", ""),
            analysis_type=state.get("analysis_type", ""),
            created_at=datetime.fromisoformat(state["created_at"]) if state.get("created_at") else datetime.utcnow(),
            last_saved_to_blob=datetime.fromisoformat(state["last_saved_to_blob"]) if state.get("last_saved_to_blob") else datetime.utcnow(),
            docx_files=state.get("docx_files", []),
            project_id=state.get("project_id"),
            epicos_report=_normalize("epicos_report"),
            features_report=_normalize("features_report"),
            times_descricao_report=_normalize("times_descricao_report"),
            alocacao_times_report=_normalize("alocacao_times_report"),
            premissas_riscos_report=_normalize("premissas_riscos_report")
        )
