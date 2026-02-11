from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class CreateProjectRequest(BaseModel):
    nome_projeto: str = Field(..., description="Nome do projeto a ser criado.")
    email: EmailStr = Field(..., description="Email do usuário solicitante.")
    empresa: str = Field(..., description="Empresa do usuário.")
    agent_name: str = Field(..., description="Nome do agente AI que será utilizado.")

class CreateProjectResponse(BaseModel):
    success: bool = Field(..., description="Indica se a criação do projeto foi bem-sucedida.")
    project_id: Optional[str] = Field(None, description="Identificador único do projeto criado.")
    message: str = Field(..., description="Mensagem de confirmação ou erro da criação do projeto.")
