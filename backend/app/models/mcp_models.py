from pydantic import BaseModel, Field, validator
from typing import Optional

class MCPStartAnalysisPayload(BaseModel):
    project_id: str = Field(..., description="Identificador único do projeto.")
    comentario_extra: Optional[str] = Field(None, description="Comentário adicional enviado pelo usuário.")
    analysis_type: str = Field(..., description="Tipo de análise a ser realizada pelo MCP.")
    job_id: str = Field(..., description="Identificador único do job.")
    # Removido: arquivo_docx

    @validator('job_id')
    def job_id_must_not_be_empty(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError('job_id é obrigatório e não pode ser vazio')
        return v

class MCPStartAnalysisResponse(BaseModel):
    project_id: str = Field(..., description="Identificador único do projeto.")
