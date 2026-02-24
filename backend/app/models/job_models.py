from pydantic import BaseModel, Field, validator
from typing import Literal, Optional, Dict
from datetime import datetime

class JobData(BaseModel):
    job_id: str = Field(...)
    project_id: str = Field(...)
    analysis_type: str = Field(...)
    status: Literal['pending', 'in_progress', 'done', 'error'] = Field(...)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    request_timestamp: datetime = Field(...)
    response_timestamp: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    email: Optional[str] = Field(default=None)
    empresa: Optional[str] = Field(default=None)
    context_used: Optional[Dict[str, str]] = Field(default_factory=dict)

    @validator('job_id', 'project_id', 'analysis_type')
    def not_empty(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError('Campo obrigatório não pode ser vazio')
        return v # ⚠️ Faltava retornar o 'v' aqui no seu validador original!
