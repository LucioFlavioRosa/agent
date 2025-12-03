from typing import Optional
from pydantic import BaseModel, Field

class UploadDocxResponse(BaseModel):
    message: str = Field(..., description="Mensagem de status do upload.")
    blob_url: str = Field(..., description="URL do arquivo salvo no blob storage.")
    job_id: str = Field(..., description="Identificador do job relacionado ao upload.")
    session_id: Optional[str] = Field(None, description="ID da sessão criada no Redis.")
    extracted_text: Optional[str] = Field(None, description="Texto extraído do documento DOCX.")
