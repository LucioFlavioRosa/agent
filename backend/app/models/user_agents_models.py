from pydantic import BaseModel, EmailStr, Field
from typing import List

class UserAgentsRequest(BaseModel):
    email: EmailStr = Field(..., description="Email do usuário")
    empresa: str = Field(..., description="Empresa do usuário (ID ou nome)")

class UserAgentsResponse(BaseModel):
    allowed_agents: List[str] = Field(..., description="Lista de agentes que o usuário pode acessar")
