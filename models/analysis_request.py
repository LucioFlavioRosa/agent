from pydantic import BaseModel, Field
from typing import Optional, List

class AnalysisRequest(BaseModel):
    repository_type: str = Field(..., description="Tipo do repositório (github, gitlab ou azure)")
    repo_name: str = Field(..., description="Nome do repositório (ex: org/projeto/repo)")
    branch_name: str = Field(..., description="Nome da branch para análise")
    agent_type: str = Field(..., description="Tipo de agente a ser executado")
    arquivos_especificos: Optional[List[str]] = Field(None, description="Lista de arquivos específicos para análise")
    instrucoes_extras: Optional[str] = Field(None, description="Instruções extras para o agente")
