from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional, Any
from datetime import datetime

class User(BaseModel):
    id: str = Field(..., alias="_id")
    email: EmailStr
    name: str
    company_id: str
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
    company_id: str
    allowed_agents: List[str] = Field(default_factory=list)
    settings: Optional[dict] = None

class ProjectMember(BaseModel):
    user_id: str
    email: EmailStr
    role: str
    added_at: Optional[datetime]

class Project(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    description: Optional[str] = None
    company_id: str
    blob_path: Optional[str] = None
    members: List[ProjectMember] = Field(default_factory=list)
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

class Company(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    domain: Optional[str] = None
    created_at: Optional[datetime]

# Para uso com motor, os campos id devem ser string (ObjectId convertido para str)
