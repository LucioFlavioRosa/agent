from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional

class UserPermission(BaseModel):
    id: str = Field(..., alias="_id")
    email: EmailStr
    name: str
    company_id: str
    active: bool = True
    group_ids: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None

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
    added_at: Optional[str] = None

class ProjectPermission(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    description: Optional[str] = None
    company_id: str
    blob_path: Optional[str] = None
    members: List[ProjectMember] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @validator('members', pre=True, always=True)
    def validate_members(cls, v):
        if not isinstance(v, list):
            raise ValueError('members deve ser uma lista')
        return v
