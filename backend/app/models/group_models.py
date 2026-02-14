from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any

class GroupDetail(BaseModel):
    id: str = Field(..., alias="_id", description="Identificador único do grupo")
    name: str = Field(..., description="Nome do grupo")
    company_id: str = Field(..., description="Identificador da empresa associada ao grupo")
    allowed_agents: List[str] = Field(default_factory=list, description="Lista de agentes/ferramentas permitidas para o grupo")
    settings: Optional[Dict[str, Any]] = Field(None, description="Configurações extras do grupo")

    @validator('allowed_agents', pre=True, always=True)
    def validate_allowed_agents(cls, v):
        if not isinstance(v, list):
            raise ValueError('allowed_agents deve ser uma lista de strings')
        if not all(isinstance(agent, str) for agent in v):
            raise ValueError('Todos os elementos de allowed_agents devem ser strings')
        return v

    @validator('company_id')
    def validate_company_id(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError('company_id é obrigatório e não pode ser vazio')
        return v
