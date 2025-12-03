from pydantic import BaseModel, Field
from typing import Dict, List

class MCPAgentConfig(BaseModel):
    agent_name: str = Field(...)
    mcp_url: str = Field(...)
    report_fields: List[str] = Field(default_factory=list)
    report_mapping: Dict[str, str] = Field(default_factory=dict)

class MCPConfigRegistry(BaseModel):
    agents: Dict[str, MCPAgentConfig] = Field(default_factory=dict)
