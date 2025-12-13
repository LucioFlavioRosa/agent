from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ProjectListItem(BaseModel):
    nome_projeto: str = Field(...)
    ultima_analysis_type: Optional[str] = Field(None, alias="ultima_analysis_type")
    created_at: Optional[datetime] = Field(None)
    last_saved_to_blob: Optional[datetime] = Field(None)
    project_id: Optional[str] = Field(default=None)
    job_id: Optional[str] = Field(default=None)
