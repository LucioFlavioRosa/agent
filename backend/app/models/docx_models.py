from pydantic import BaseModel, Field

class UploadDocxResponse(BaseModel):
    message: str = Field(..., description="Mensagem de status do upload.")
    project_id: str = Field(..., description="Identificador único do projeto.")
