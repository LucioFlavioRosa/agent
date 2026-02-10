from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class UserProjectAccessResponse(BaseModel):
    project_id: str = Field(..., description="Identificador único do projeto")
    project_name: str = Field(..., description="Nome do projeto")
    role: str = Field(..., description="Nível de acesso do usuário no projeto: owner/editor/viewer")
    description: Optional[str] = Field(None, description="Descrição do projeto")
    created_at: Optional[datetime] = Field(None, description="Data de criação do projeto")

class UserProjectsListResponse(BaseModel):
    projects: List[UserProjectAccessResponse] = Field(..., description="Lista de projetos com acesso do usuário")
