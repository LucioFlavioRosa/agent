from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional, Any, Dict
from datetime import datetime
import uuid

class User(BaseModel):
    id: str = Field(..., alias="_id")
    email: EmailStr
    name: str
    company_id: str = Field(...)
    active: bool = True
    group_ids: List[str] = Field(default_factory=list)
    created_at: Optional[datetime]

    @validator('email')
    def email_must_be_valid(cls, v):
        if not v:
            raise ValueError('Email é obrigatório')
        return v

class Group(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    company_id: str = Field(...)
    allowed_agents: List[str] = Field(default_factory=list)
    settings: Optional[Dict[str, Any]] = None

class ProjectMember(BaseModel):
    user_id: str
    email: EmailStr
    role: str
    added_at: Optional[datetime]

    @validator('role')
    def role_must_be_valid(cls, v):
        valid_roles = {'owner', 'editor', 'viewer'}
        if v not in valid_roles:
            raise ValueError(f"Role inválida: {v}. Deve ser uma das {valid_roles}.")
        return v

class Project(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    description: Optional[str] = None
    company_id: str = Field(...)
    blob_path: Optional[str] = None
    members: List[ProjectMember] = Field(default_factory=list)
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    @classmethod
    def create_new_project(cls, name: str, company_id: str, owner_user_id: str, owner_email: str, description: Optional[str] = None, blob_path: Optional[str] = None) -> "Project":
        project_id = str(uuid.uuid4())
        now = datetime.utcnow()
        owner_member = ProjectMember(
            user_id=owner_user_id,
            email=owner_email,
            role="owner",
            added_at=now
        )
        return cls(
            id=project_id,
            name=name,
            description=description,
            company_id=company_id,
            blob_path=blob_path,
            members=[owner_member],
            created_at=now,
            updated_at=now
        )

class Company(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    domain: Optional[str] = None
    created_at: Optional[datetime]
