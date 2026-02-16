from pydantic import BaseModel, Field
from typing import List, Optional

class AgentAccessResponse(BaseModel):
    agent_name: str = Field(..., description="Nome do agente permitido para o usuário")
    description: Optional[str] = Field(None, description="Descrição opcional do agente")

class UserAgentsListResponse(BaseModel):
    agents: List[AgentAccessResponse] = Field(..., description="Lista de agentes permitidos para o usuário")
