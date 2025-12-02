from typing import Optional
from fastapi import UploadFile
from pydantic import BaseModel, Field

class UploadWithCommentRequest(BaseModel):
    file: UploadFile = Field(...)
    projeto: str = Field(...)
    analysis_name: str = Field(...)
    is_new_project: bool = Field(True)
    session_id: Optional[str] = Field(None)
    analysis_type: Optional[str] = Field(None)
    user_comment: Optional[str] = Field(None)