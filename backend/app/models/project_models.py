from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ProjectListItem(BaseModel):
    projeto: str = Field(...)
    analysis_type: Optional[str] = Field(None)
    created_at: Optional[datetime] = Field(None)
    last_saved_to_blob: Optional[datetime] = Field(None)
