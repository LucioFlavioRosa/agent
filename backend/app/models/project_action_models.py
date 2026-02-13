from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class ProjectActionRequest(BaseModel):
    email: EmailStr = Field(..., description="Email do usuário que solicita a ação")
    project_id: str = Field(..., description="ID do projeto alvo da ação")
    action_type: str = Field(..., description="Tipo de ação solicitada: 'view', 'edit', 'delete', 'add_member'")

class ProjectActionResponse(BaseModel):
    success: bool = Field(..., description="Indica se a ação é permitida")
    allowed: bool = Field(..., description="Indica se a ação é permitida para o usuário e role")
    role: Optional[str] = Field(None, description="Role do usuário no projeto")
    message: Optional[str] = Field(None, description="Mensagem de erro ou confirmação")
