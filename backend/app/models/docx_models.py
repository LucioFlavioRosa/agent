from typing import Optional
from pydantic import BaseModel, Field
from fastapi import UploadFile

class UploadDocxResponse(BaseModel):
    message: str = Field(..., description="Mensagem de status do upload.")
    blob_url: str = Field(..., description="URL do arquivo salvo no blob storage.")
    job_id: str = Field(..., description="Identificador do job relacionado ao upload.")
