from pydantic import BaseModel, Field
from fastapi import UploadFile
from typing import Optional

class DocxUploadRequest(BaseModel):
    projeto: str = Field(..., description="Nome do projeto ao qual o arquivo DOCX pertence.")
    analysis_name: str = Field(..., description="Nome da análise/tarefa associada ao upload.")
    # O campo 'file' será tratado diretamente como UploadFile na rota FastAPI, não como campo Pydantic

class DocxUploadResponse(BaseModel):
    blob_url: str = Field(..., description="URL do arquivo DOCX salvo no blob storage.")
    extracted_text: str = Field(..., description="Texto extraído do arquivo DOCX.")
    job_id: str = Field(..., description="Identificador do job/processo relacionado ao upload.")
