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
    
    # --- NOVO CAMPO (Correção do Erro 500) ---
    ultima_atualizacao: Optional[datetime] = Field(default=None, description="Data da última modificação de qualquer dado no Redis")
    # -----------------------------------------
    
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
            
            # --- SERIALIZAÇÃO DO NOVO CAMPO ---
            "ultima_atualizacao": self.ultima_atualizacao.isoformat() if self.ultima_atualizacao else None,
            # ----------------------------------
            
            "docx_files": self.docx_files,
            "project_id": self.project_id,
            "epicos_report": self.epicos_report,
            "features_report": self.features_report,
            "times_descricao_report": self.times_descricao_report,
            "alocacao_times_report": self.alocacao_times_report,
            "premissas_riscos_report": self.premissas_riscos_report
        }
        # Limpeza de campos legados ou temporários
        state.pop("projeto", None)
        state.pop("comentario_usuario", None)
        state.pop("docx_blob_url", None)
        state.pop("extracted_text", None)
        return state

    @classmethod
    def from_project_state(cls, state: Dict[str, Any]) -> "SessionData":
        logger = logging.getLogger("SessionData")
        
        # Helper interno para converter string ISO em datetime sem erros
        def parse_datetime(val):
            if not val:
                return None
            if isinstance(val, datetime):
                return val
            try:
                return datetime.fromisoformat(str(val))
            except:
                return None

        # Definição de defaults seguros
        created_at_val = parse_datetime(state.get("created_at")) or datetime.utcnow()
        last_saved_val = parse_datetime(state.get("last_saved_to_blob")) or datetime.utcnow()
        ultima_atualizacao_val = parse_datetime(state.get("ultima_atualizacao"))

        return cls(
            usuario_executor=state.get("usuario_executor", ""),
            nome_projeto=state.get("nome_projeto", ""),
            analysis_type=state.get("analysis_type", ""),
            created_at=created_at_val,
            last_saved_to_blob=last_saved_val,
            
            # --- DESSERIALIZAÇÃO DO NOVO CAMPO ---
            ultima_atualizacao=ultima_atualizacao_val,
            # -------------------------------------
            
            docx_files=state.get("docx_files", []),
            project_id=state.get("project_id"),
            epicos_report=state.get("epicos_report"),
            features_report=state.get("features_report"),
            times_descricao_report=state.get("times_descricao_report"),
            alocacao_times_report=state.get("alocacao_times_report"),
            premissas_riscos_report=state.get("premissas_riscos_report")
        )
