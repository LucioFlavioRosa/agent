from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime

class FrontendToBackendPayload(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    endpoint: str
    method: str
    payload_data: Any
    usuario_executor: Optional[str] = None
    project_id: Optional[str] = None
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class BackendToFrontendPayload(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    endpoint: str
    status_code: int
    response_data: Any
    usuario_executor: Optional[str] = None
    project_id: Optional[str] = None
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class MCPToBackendPayload(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    webhook_type: str
    payload_data: Any
    project_id: Optional[str] = None
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class BackendToMCPPayload(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    analysis_type: str
    payload_data: Any
    project_id: Optional[str] = None
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
