from typing import Optional
from pydantic import BaseModel, Field

class UploadDocxResponse(BaseModel):
    message: str = Field(..., description="Mensagem de status do upload.")
    blob_url: str = Field(..., description="URL do arquivo salvo no blob storage.")
    extracted_text: Optional[str] = Field(None, description="Texto extraído do documento DOCX.")
    project_id: str = Field(..., description="Identificador único do projeto.")
    nome_projeto: Optional[str] = Field(None, description="Nome legível do projeto.")
