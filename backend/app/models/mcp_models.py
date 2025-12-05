from pydantic import BaseModel, Field, validator
from typing import Optional

class MCPStartAnalysisPayload(BaseModel):
    projeto: str = Field(..., description="Nome do projeto.")
    analysis_type: str = Field(..., description="Tipo de análise a ser realizada pelo MCP.")
    arquivo_docx: Optional[str] = Field(None, description="Texto extraído do arquivo docx com a transcrição da reunião. NÃO é a URL do Blob Storage.")
    comentario_usuario: Optional[str] = Field(None, description="Comentário adicional enviado pelo usuário.")
    usuario_executor: str = Field(..., description="Usuário executor extraído do token JWT.")
    session_id: str = Field(..., description="Identificador da sessão.")

    @validator('analysis_type')
    def analysis_type_must_not_be_empty(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError('analysis_type deve ser uma string não vazia')
        return v

class MCPStartAnalysisResponse(BaseModel):
    job_id: str = Field(..., description="Identificador do job criado no MCP.")
