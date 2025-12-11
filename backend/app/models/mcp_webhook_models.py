from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, Any, Literal, Dict

class MCPWebhookPayload(BaseModel):
    job_id: str = Field(...)
    status: Literal['in_progress', 'done', 'error'] = Field(...)
    progress: Optional[int] = Field(None)
    report_data: Optional[Dict[str, Any]] = Field(None)
    error_type: Optional[str] = Field(None)
    error_message: Optional[str] = Field(None)
    project_id: Optional[str] = Field(None)

    @validator('job_id')
    def job_id_must_not_be_empty(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError('job_id deve ser uma string não vazia')
        return v

    @validator('status')
    def status_must_be_valid(cls, v):
        allowed = {'in_progress', 'done', 'error'}
        if v not in allowed:
            raise ValueError(f"status deve ser um dos: {allowed}")
        return v

    @root_validator(skip_on_failure=True)
    def validate_report_data_structure(cls, values):
        status = values.get('status')
        report_data = values.get('report_data')
        valid_report_fields = [
            "epicos_report",
            "features_report",
            "times_descricao_report",
            "alocacao_times_report",
            "premissas_riscos_report"
        ]
        if status in {'in_progress', 'done'}:
            if report_data is None or not isinstance(report_data, dict) or len(report_data) != 1:
                raise ValueError("report_data deve ser um dicionário com exatamente uma chave quando status é 'in_progress' ou 'done'")
            report_field = list(report_data.keys())[0]
            if report_field not in valid_report_fields:
                raise ValueError(f"Chave de relatório '{report_field}' não é válida. Esperado uma das: {valid_report_fields}")
            value = report_data[report_field]
            if not isinstance(value, list):
                raise ValueError(f"O valor da chave '{report_field}' deve ser uma lista")
        if status == 'error':
            if not values.get('error_message'):
                raise ValueError("error_message é obrigatório quando status é 'error'")
        return values
