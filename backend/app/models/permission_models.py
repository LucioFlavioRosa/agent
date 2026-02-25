from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional, Dict, Union, Any
from datetime import datetime

class UserPermission(BaseModel):
    id: str = Field(..., alias="_id")
    email: EmailStr
    name: str
    company_id: str
    active: bool = True
    group_ids: List[str] = Field(default_factory=list)
    created_at: Optional[Union[datetime, str]] = None

    @validator('email')
    def email_must_be_valid(cls, v):
        if not v:
            raise ValueError('Email é obrigatório')
        return v

class GroupPermission(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    company_id: str
    allowed_agents: List[str] = Field(default_factory=list)
    settings: Optional[dict] = None

class ProjectMember(BaseModel):
    user_id: str
    email: EmailStr
    role: str
    # CORREÇÃO AQUI: Aceita ambos, pois seu código gera string ISO, 
    # mas o Mongo pode salvar/retornar datetime.
    added_at: Optional[Union[datetime, str]] = None

    @validator('role')
    def role_must_be_valid(cls, v):
        valid_roles = {'owner', 'editor', 'viewer'}
        if v not in valid_roles:
            raise ValueError(f"Role inválida: {v}. Deve ser uma das {valid_roles}.")
        return v

class ProjectPermission(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    description: Optional[str] = None
    company_id: str
    blob_path: Optional[str] = None
    members: List[ProjectMember] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    latest_reports: Dict[str, Any] = {}

    @validator('members', pre=True, always=True)
    def validate_members(cls, v):
        if not isinstance(v, list):
            raise ValueError('members deve ser uma lista')
        return v

class UserPermissionCache(BaseModel):
    email: EmailStr = Field(..., description="Email do usuário")
    company_id: str = Field(..., description="ID da empresa do usuário")
    allowed_agents: List[str] = Field(default_factory=list, description="Lista de agentes permitidos para o usuário")
    project_permissions: Dict[str, dict] = Field(default_factory=dict, description="Mapa de project_id para role e ações do usuário no projeto")
    cached_at: str = Field(..., description="Timestamp ISO de quando o cache foi gerado")

    @validator('email')
    def email_must_be_valid(cls, v):
        if not v:
            raise ValueError('Email é obrigatório')
        return v

    @validator('company_id')
    def company_id_must_be_valid(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError('company_id é obrigatório e não pode ser vazio')
        return v

    @validator('cached_at')
    def cached_at_must_be_iso(cls, v):
        try:
            # Apenas valida se é uma string ISO válida, não altera o tipo
            datetime.fromisoformat(v)
        except Exception:
            raise ValueError('cached_at deve ser um timestamp ISO válido')
        return v
