from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class AnalysisReport(BaseModel):
    job_id: str = Field(..., description="Identificador do job")
    project_id: str = Field(..., description="Identificador do projeto")
    company_id: str = Field(..., description="Identificador da empresa")
    email: str = Field(..., description="Email do usuário")
    analysis_type: str = Field(..., description="Tipo de análise (ex: agent_epics_generator_digital)")
    report_type: str = Field(..., description="Tipo de relatório (epics/features/timeline/risks)")
    report_content: str = Field(..., description="Conteúdo do relatório em markdown")
    extra_comment: Optional[str] = Field(None, description="Comentário extra em markdown")
    document_path: Optional[str] = Field(None, description="Caminho do documento recebido no blob storage")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Data de criação do relatório")
    status: str = Field(..., description="Status do relatório (ex: pending, completed, failed)")
