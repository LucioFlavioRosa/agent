from typing import Optional
from pydantic import BaseModel, Field
from fastapi import UploadFile

class UploadDocxRequest(BaseModel):
    projeto: str = Field(..., description="Nome do projeto ao qual o arquivo pertence.")
    analysis_name: str = Field(..., description="Nome da tarefa/analise para identificação.")
    # O campo 'file' será tratado diretamente no endpoint FastAPI como UploadFile, não como campo Pydantic.

class UploadDocxResponse(BaseModel):
    message: str = Field(..., description="Mensagem de status do upload.")
    blob_url: str = Field(..., description="URL do arquivo salvo no blob storage.")
    job_id: str = Field(..., description="Identificador do job relacionado ao upload.")
