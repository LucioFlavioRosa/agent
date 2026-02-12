from pydantic import BaseModel, Field, field_validator
from typing import Optional

class MCPStartAnalysisPayload(BaseModel):
    project_id: str = Field(..., description="ID único do projeto no MongoDB")
    job_id: str = Field(..., description="ID único da execução (UUID)")
    email: Optional[str] = None
    nome_projeto: Optional[str] = None
    agent_name: Optional[str] = None
    analysis_type: Optional[str] = None
    branch: Optional[str] = None
    repository: Optional[str] = None
    comentario_extra: Optional[str] = None

    @field_validator('job_id', 'project_id', mode='before')
    @classmethod
    def fields_not_empty(cls, v):
        """
        Garante que os IDs não sejam nulos, vazios ou apenas espaços.
        O modo 'before' garante a validação antes mesmo da conversão final.
        """
        if v is None:
            raise ValueError('Este campo não pode ser nulo')
        if isinstance(v, str) and not v.strip():
            raise ValueError('Este campo não pode estar vazio ou conter apenas espaços')
        return v

class MCPStartAnalysisResponse(BaseModel):
    project_id: str
    job_id: Optional[str] = None
