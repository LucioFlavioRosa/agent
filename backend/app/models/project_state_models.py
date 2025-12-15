from pydantic import BaseModel, Field, validator
from typing import Optional, List, Any
from datetime import datetime

class EstadoResumoProjeto(BaseModel):
    project_id: Optional[str] = Field(None)
    last_job_id: Optional[str] = Field(None, description="ID do último job concluído com sucesso")
    nome_projeto: str = Field(...)
    ultima_analysis_type: Optional[str] = Field(None)
    created_at: datetime = Field(...)
    ultima_atualizacao: datetime = Field(...)
    usuario_executor: Optional[str] = Field(None)

    @validator('nome_projeto')
    def nome_projeto_must_not_be_empty(cls, v):
        if v is None or not isinstance(v, str) or not v.strip():
            raise ValueError("Campo 'nome_projeto' é obrigatório e não pode ser None ou vazio para criar o estado de resumo.")
        return v

class EstadoEpicos(BaseModel):
    project_id: Optional[str] = Field(None)
    nome_projeto: str = Field(...)
    ultima_analysis_type: Optional[str] = Field(None)
    created_at: datetime = Field(...)
    ultima_atualizacao: datetime = Field(...)
    epicos_report: List[Any] = Field(default_factory=list)
    job_id: Optional[str] = Field(None)

class EstadoEpicosTimeline(BaseModel):
    project_id: Optional[str] = Field(None)
    nome_projeto: str = Field(...)
    ultima_analysis_type: Optional[str] = Field(None)
    created_at: datetime = Field(...)
    ultima_atualizacao: datetime = Field(...)
    epicos_report: List[Any] = Field(default_factory=list)
    job_id: Optional[str] = Field(None)

class EstadoFeatures(BaseModel):
    project_id: Optional[str] = Field(None)
    nome_projeto: str = Field(...)
    ultima_analysis_type: Optional[str] = Field(None)
    created_at: datetime = Field(...)
    ultima_atualizacao: datetime = Field(...)
    features_report: List[Any] = Field(default_factory=list)
    job_id: Optional[str] = Field(None)

class EstadoAlocacaoTimes(BaseModel):
    project_id: Optional[str] = Field(None)
    nome_projeto: str = Field(...)
    ultima_analysis_type: Optional[str] = Field(None)
    created_at: datetime = Field(...)
    ultima_atualizacao: datetime = Field(...)
    alocacao_times_report: List[Any] = Field(default_factory=list)
    job_id: Optional[str] = Field(None)

class EstadoPremissasRiscos(BaseModel):
    project_id: Optional[str] = Field(None)
    nome_projeto: str = Field(...)
    ultima_analysis_type: Optional[str] = Field(None)
    created_at: datetime = Field(...)
    ultima_atualizacao: datetime = Field(...)
    premissas_riscos_report: List[Any] = Field(default_factory=list)
    job_id: Optional[str] = Field(None)

class EstadoCompletoProjetoResponse(BaseModel):
    last_job_id: Optional[str] = Field(None)
    resumo: Optional[EstadoResumoProjeto] = None
    epicos: Optional[EstadoEpicos] = None
    epicos_timeline: Optional[EstadoEpicosTimeline] = None
    features: Optional[EstadoFeatures] = None
    alocacao_times: Optional[EstadoAlocacaoTimes] = None
    premissas_riscos: Optional[EstadoPremissasRiscos] = None
