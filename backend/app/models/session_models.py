from pydantic import BaseModel, Field
from typing import Optional

class SessionData(BaseModel):
    job_id: str = Field(..., description="Identificador único do job.")
    status: str = Field(..., description="Status do job.")
    # Apenas campos essenciais para rastrear jobs; demais campos removidos conforme nova responsabilidade do backend.