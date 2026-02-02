from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

class RepositoryType(str, Enum):
    github = 'github'
    gitlab = 'gitlab'
    azure = 'azure'

class AnalysisType(str, Enum):
    review_code = 'review_code'
    improve_code = 'improve_code'

class AnalysisConfig(BaseModel):
    repo_name: str = Field(..., description="Nome do repositório a ser analisado")
    branch_name: str = Field(..., description="Nome da branch do repositório")
    repository_type: RepositoryType = Field(..., description="Tipo do repositório: github, gitlab, azure")
    analysis_type: AnalysisType = Field(..., description="Tipo de análise: revisão ou melhoria de código")
    arquivos_especificos: Optional[List[str]] = Field(None, description="Lista opcional de arquivos específicos para análise")
    instrucoes_extras: Optional[str] = Field(None, description="Instruções extras para o agente de análise")
    usar_rag: bool = Field(False, description="Se True, utiliza RAG para contexto adicional")
    model_name: Optional[str] = Field(None, description="Nome do modelo de LLM a ser usado")
