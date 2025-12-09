from pydantic import BaseModel, Field, validator
from typing import Optional

class MCPStartAnalysisPayload(BaseModel):
    projeto: str = Field(..., description="Nome do projeto.")
    analysis_type: str = Field(..., description="Tipo de análise a ser realizada pelo MCP.")
    arquivo_docx: Optional[str] = Field(None, description="Texto extraído do arquivo docx com a transcrição da reunião. NÃO é a URL do Blob Storage.")
    comentario_usuario: Optional[str] = Field(None, description="Comentário adicional enviado pelo usuário.")
    usuario_executor: str = Field(..., description="Usuário executor extraído do token JWT.")
    project_id: str = Field(..., description="Identificador único do projeto.")
    nome_projeto: Optional[str] = Field(None, description="Nome legível do projeto (apenas para log/debug).")

    @validator('analysis_type')
    def analysis_type_must_not_be_empty(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError('analysis_type deve ser uma string não vazia')
        return v

    @validator('project_id')
    def project_id_must_not_be_empty(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError('project_id deve ser uma string não vazia')
        return v

class MCPStartAnalysisResponse(BaseModel):
    project_id: str = Field(..., description="Identificador único do projeto.")
