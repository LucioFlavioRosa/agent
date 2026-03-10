from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List

class MCPStartAnalysisPayload(BaseModel):
    project_id: str = Field(..., description="ID único do projeto no MongoDB")
    job_id: str = Field(..., description="ID único da execução (UUID)")
    
    # Campos que estavam faltando e são vitais:
    company_id: str = Field(..., description="ID da empresa para buscar o Vault/Blob")
    group_ids: Optional[List[str]] = Field(default_factory=list, description="Grupos do projeto")
    context_used: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Linhagem do prompt chaining")
    
    # Campos normais
    email: Optional[str] = None
    nome_projeto: Optional[str] = None
    agent_name: Optional[str] = None
    analysis_type: Optional[str] = None
    branch: Optional[str] = None
    repository: Optional[str] = None
    comentario_extra: Optional[str] = None

    @field_validator('job_id', 'project_id', 'company_id', mode='before')
    @classmethod
    def fields_not_empty(cls, v):
        """
        Garante que os IDs essenciais não sejam nulos, vazios ou apenas espaços.
        """
        if v is None:
            raise ValueError('Este campo não pode ser nulo')
        if isinstance(v, str) and not v.strip():
            raise ValueError('Este campo não pode estar vazio ou conter apenas espaços')
        return v

class MCPStartAnalysisResponse(BaseModel):
    project_id: str
    job_id: Optional[str] = None
