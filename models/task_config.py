from pydantic import BaseModel

class TaskConfig(BaseModel):
    description: str
    status_update: str
    model_name: str
    agent_type: str
    instrucoes_extras: str
    provider: Optional[str] = None
