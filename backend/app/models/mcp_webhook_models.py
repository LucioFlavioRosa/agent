from pydantic import BaseModel, Field
from typing import Optional, Any, Literal, Dict

class MCPWebhookPayload(BaseModel):
    job_id: str = Field(...)
    status: Literal['in_progress', 'done', 'error'] = Field(...)
    progress: Optional[int] = Field(None)
    report_data: Optional[Dict[str, Any]] = Field(None)
    error_type: Optional[str] = Field(None)
    error_message: Optional[str] = Field(None)
    project_id: Optional[str] = Field(None)
    # Nenhuma validação de estrutura de report_data, apenas repassa o conteúdo recebido
