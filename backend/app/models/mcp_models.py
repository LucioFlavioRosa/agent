from pydantic import BaseModel, Field
from typing import Optional

class MCPStartAnalysisPayload(BaseModel):
    analysis_type: str = Field(..., description="Tipo de análise a ser realizada pelo MCP.")
    instrucoes_extras: str = Field(..., description="Texto extraído do arquivo docx com a transcrição da reunião.")
    projeto: str = Field(..., description="Nome do projeto.")
    analysis_name: str = Field(..., description="Nome da tarefa/analise.")
    usuario_executor: str = Field(..., description="Usuário executor extraído do token JWT.")

class MCPStartAnalysisResponse(BaseModel):
    job_id: str = Field(..., description="Identificador do job criado no MCP.")
