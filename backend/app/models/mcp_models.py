from pydantic import BaseModel, Field, validator
from typing import Optional

class MCPStartAnalysisPayload(BaseModel):
    analysis_type: str = Field(..., description="Tipo de análise a ser realizada pelo MCP.")
    instrucoes_extras: str = Field(..., description="Texto extraído do arquivo docx com a transcrição da reunião.")
    projeto: str = Field(..., description="Nome do projeto.")
    analysis_name: str = Field(..., description="Nome da tarefa/analise.")
    usuario_executor: str = Field(..., description="Usuário executor extraído do token JWT.")

    @validator('analysis_type')
    def analysis_type_must_not_be_empty(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError('analysis_type deve ser uma string não vazia')
        return v

class MCPStartAnalysisResponse(BaseModel):
    job_id: str = Field(..., description="Identificador do job criado no MCP.")
