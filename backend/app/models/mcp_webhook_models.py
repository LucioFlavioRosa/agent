from pydantic import BaseModel, Field, validator
from typing import Optional, Any, Literal

class MCPWebhookPayload(BaseModel):
    job_id: str = Field(...)
    status: Literal['in_progress', 'done', 'error'] = Field(...)
    progress: Optional[int] = Field(None)
    report_type: Optional[str] = Field(None)
    report_data: Optional[Any] = Field(None)
    error_type: Optional[str] = Field(None)
    error_message: Optional[str] = Field(None)
    project_id: str = Field(..., description="Identificador único do projeto.")

    @validator('status')
    def status_must_be_valid(cls, v):
        allowed = {'in_progress', 'done', 'error'}
        if v not in allowed:
            raise ValueError(f"status deve ser um dos: {allowed}")
        return v

    @validator('report_data', always=True)
    def report_data_required_for_status(cls, v, values):
        status = values.get('status')
        if status in {'in_progress', 'done'}:
            if v is None:
                raise ValueError("report_data é obrigatório quando status é 'in_progress' ou 'done'")
            if not isinstance(v, dict):
                raise ValueError("report_data deve ser um dicionário")
        return v

    @validator('error_message', always=True)
    def error_message_required_for_error(cls, v, values):
        status = values.get('status')
        if status == 'error' and not v:
            raise ValueError("error_message é obrigatório quando status é 'error'")
        return v

    @validator('project_id', always=True)
    def project_id_must_be_present(cls, v, values):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError('project_id é obrigatório e deve ser uma string não vazia')
        return v
