from pydantic import BaseModel, Field, validator
from typing import Optional

class MCPStartAnalysisPayload(BaseModel):
    project_id: str = Field(..., description="Identificador único do projeto.")
    comentario_extra: Optional[str] = Field(None, description="Comentário adicional enviado pelo usuário.")
    analysis_type: str = Field(..., description="Tipo de análise a ser realizada pelo MCP.")
    job_id: str = Field(..., description="Identificador único do job.")

    @validator('analysis_type')
    def analysis_type_must_not_be_empty(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError('analysis_type deve ser uma string não vazia')
        return v

    @validator('project_id')
    def project_id_must_not_be_empty(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError('project_id deve ser uma string não vazia')
        return v

    @validator('job_id')
    def job_id_must_not_be_empty(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError('job_id deve ser uma string não vazia')
        return v

class MCPStartAnalysisResponse(BaseModel):
    project_id: str = Field(..., description="Identificador único do projeto.")
