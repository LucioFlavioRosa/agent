from pydantic import BaseModel, Field, validator, root_validator
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

    @root_validator
    def at_least_one_text_field(cls, values):
        arquivo_docx = values.get('arquivo_docx')
        comentario_usuario = values.get('comentario_usuario')
        if (not arquivo_docx or not str(arquivo_docx).strip()) and (not comentario_usuario or not str(comentario_usuario).strip()):
            raise ValueError('É obrigatório fornecer pelo menos arquivo_docx (texto extraído) ou comentario_usuario.')
        return values

class MCPStartAnalysisResponse(BaseModel):
    project_id: str = Field(..., description="Identificador único do projeto.")
