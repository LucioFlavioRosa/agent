from pydantic import BaseModel, Field, validator
from typing import Optional, List, Any
from datetime import datetime

class EstadoResumoProjeto(BaseModel):
    nome_projeto: str = Field(...)
    ultima_analysis_type: Optional[str] = Field(None)
    created_at: datetime = Field(...)
    ultima_atualizacao: datetime = Field(...)

    @validator('nome_projeto')
    def nome_projeto_must_not_be_empty(cls, v):
        if v is None or not isinstance(v, str) or not v.strip():
            raise ValueError("Campo 'nome_projeto' é obrigatório e não pode ser None ou vazio para criar o estado de resumo.")
        return v

class EstadoEpicos(BaseModel):
    nome_projeto: str = Field(...)
    ultima_analysis_type: Optional[str] = Field(None)
    created_at: datetime = Field(...)
    ultima_atualizacao: datetime = Field(...)
    epicos_report: List[Any] = Field(default_factory=list)

class EstadoFeatures(BaseModel):
    nome_projeto: str = Field(...)
    ultima_analysis_type: Optional[str] = Field(None)
    created_at: datetime = Field(...)
    ultima_atualizacao: datetime = Field(...)
    features_report: List[Any] = Field(default_factory=list)

class EstadoTimesDescricao(BaseModel):
    nome_projeto: str = Field(...)
    ultima_analysis_type: Optional[str] = Field(None)
    created_at: datetime = Field(...)
    ultima_atualizacao: datetime = Field(...)
    times_descricao_report: List[Any] = Field(default_factory=list)

class EstadoAlocacaoTimes(BaseModel):
    nome_projeto: str = Field(...)
    ultima_analysis_type: Optional[str] = Field(None)
    created_at: datetime = Field(...)
    ultima_atualizacao: datetime = Field(...)
    alocacao_times_report: List[Any] = Field(default_factory=list)

class EstadoPremissasRiscos(BaseModel):
    nome_projeto: str = Field(...)
    ultima_analysis_type: Optional[str] = Field(None)
    created_at: datetime = Field(...)
    ultima_atualizacao: datetime = Field(...)
    premissas_riscos_report: List[Any] = Field(default_factory=list)

class EstadoCompletoProjetoResponse(BaseModel):
    resumo: Optional[EstadoResumoProjeto] = None
    epicos: Optional[EstadoEpicos] = None
    features: Optional[EstadoFeatures] = None
    times_descricao: Optional[EstadoTimesDescricao] = None
    alocacao_times: Optional[EstadoAlocacaoTimes] = None
    premissas_riscos: Optional[EstadoPremissasRiscos] = None
