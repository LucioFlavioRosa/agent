from pydantic import BaseModel, Field
from typing import Optional

class MCPStartAnalysisPayload(BaseModel):
    project_id: str = Field(..., description="Identificador único do projeto.")
    comentario_extra: Optional[str] = Field(None, description="Comentário adicional enviado pelo usuário.")
    analysis_type: str = Field(..., description="Tipo de análise a ser realizada pelo MCP.")
    job_id: str = Field(..., description="Identificador único do job.")
    # arquivo_docx não é validado nem processado, apenas repassado no payload

class MCPStartAnalysisResponse(BaseModel):
    project_id: str = Field(..., description="Identificador único do projeto.")
