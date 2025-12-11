from pydantic import BaseModel, Field, validator
from typing import Literal
from datetime import datetime

class JobData(BaseModel):
    job_id: str = Field(...)
    project_id: str = Field(...)
    analysis_type: str = Field(...)
    status: Literal['pending', 'in_progress', 'done', 'error'] = Field(...)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)

    @validator('job_id', 'project_id', 'analysis_type')
    def not_empty(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError('Campo obrigatório não pode ser vazio')
        return v
