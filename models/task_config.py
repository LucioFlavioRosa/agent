from pydantic import BaseModel
from typing import Optional

class TaskConfig(BaseModel):
    description: str
    status_update: str
    model_name: str
    agent_type: str
    instrucoes_extras: str
    provider: Optional[str] = None
