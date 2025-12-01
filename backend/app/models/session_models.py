from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class SessionStep(BaseModel):
    step_id: str = Field(...)
    timestamp: datetime = Field(...)
    action: str = Field(...)
    status: str = Field(...)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class SessionData(BaseModel):
    session_id: str = Field(...)
    usuario_executor: str = Field(...)
    projeto: str = Field(...)
    analysis_name: str = Field(...)
    analysis_type: str = Field(...)
    created_at: datetime = Field(...)
    steps: List[SessionStep] = Field(default_factory=list)
