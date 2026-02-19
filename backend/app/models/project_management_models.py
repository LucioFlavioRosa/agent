from enum import Enum
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, validator

class ProjectRole(str, Enum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"

class ProjectIdentifierRequest(BaseModel):
    project_name: str = Field(..., description="Nome do projeto para identificação")
    company_id: str = Field(..., description="Identificador da empresa associada ao projeto")

    @validator('project_name')
    def project_name_not_empty(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError('project_name é obrigatório e não pode ser vazio')
        return v

    @validator('company_id')
    def company_id_not_empty(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError('company_id é obrigatório e não pode ser vazio')
        return v

class OwnedProjectItem(BaseModel):
    project_id: str = Field(..., description="Identificador único do projeto")
    name: str = Field(..., description="Nome do projeto")
    description: Optional[str] = Field(None, description="Descrição do projeto")
    members: List[dict] = Field(..., description="Lista de membros do projeto")

class ListOwnedProjectsResponse(BaseModel):
    projects: List[OwnedProjectItem] = Field(..., description="Lista de projetos onde o usuário é owner")

class AddProjectMemberRequest(BaseModel):
    requester_email: EmailStr = Field(..., description="Email do usuário solicitante (owner)")
    project_name: str = Field(..., description="Nome do projeto")
    new_member_email: EmailStr = Field(..., description="Email do novo membro a ser adicionado")
    role: ProjectRole = Field(..., description="Permissão do novo membro: owner, editor ou viewer")

    @validator('project_name')
    def project_name_not_empty(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError('project_name é obrigatório e não pode ser vazio')
        return v

class AddProjectMemberResponse(BaseModel):
    success: bool = Field(..., description="Indica se a adição foi bem-sucedida")
    message: Optional[str] = Field(None, description="Mensagem de confirmação ou erro")

class UpdateProjectMembersRequest(BaseModel):
    requester_email: EmailStr = Field(..., description="Email do usuário solicitante (owner)")
    project_name: str = Field(..., description="Nome do projeto")
    members: List[dict] = Field(..., description="Lista completa de membros a ser salva no projeto")

    @validator('project_name')
    def project_name_not_empty(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError('project_name é obrigatório e não pode ser vazio')
        return v

class UpdateProjectMembersResponse(BaseModel):
    success: bool = Field(..., description="Indica se a atualização foi bem-sucedida")
    message: Optional[str] = Field(None, description="Mensagem de confirmação ou erro")

class DeleteProjectRequest(BaseModel):
    requester_email: EmailStr = Field(..., description="Email do usuário solicitante (owner)")
    project_name: str = Field(..., description="Nome do projeto a ser excluído")

    @validator('project_name')
    def project_name_not_empty(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError('project_name é obrigatório e não pode ser vazio')
        return v

class DeleteProjectResponse(BaseModel):
    success: bool = Field(..., description="Indica se a exclusão foi bem-sucedida")
    message: Optional[str] = Field(None, description="Mensagem de confirmação ou erro")

class ProjectWithRoleItem(BaseModel):
    project_id: str
    project_name: str
    role: ProjectRole
    description: Optional[str] = None
    created_at: Optional[datetime] = None
