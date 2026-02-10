from pydantic import BaseModel, Field
from typing import Optional, Any, Literal, Dict

class MCPWebhookPayload(BaseModel):
    job_id: str = Field(...)
    status: Literal['in_progress', 'done', 'error'] = Field(...)
    progress: Optional[int] = Field(None)
    report_data: Optional[Dict[str, Any]] = Field(None, description="Conteúdo do relatório enviado pelo MCP. Nenhuma validação de estrutura é realizada pelo backend; o conteúdo é repassado como recebido.")
    error_type: Optional[str] = Field(None)
    error_message: Optional[str] = Field(None)
    project_id: Optional[str] = Field(None)
    # ATENÇÃO: O backend não valida a estrutura de report_data, apenas repassa o conteúdo recebido do MCP.
