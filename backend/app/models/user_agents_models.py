from pydantic import BaseModel, EmailStr, Field
from typing import List

class UserAgentsRequest(BaseModel):
    email: EmailStr = Field(..., description="Email do usuário para consulta de agentes")
    empresa: str = Field(..., description="Empresa do usuário para validação multi-tenant")

class UserAgentsResponse(BaseModel):
    allowed_agents: List[str] = Field(..., description="Lista de agentes que o usuário pode acessar")
