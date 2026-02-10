from pydantic import BaseModel, Field
from typing import Dict, List

class MCPAgentConfig(BaseModel):
    agent_name: str = Field(...)
    mcp_url: str = Field(...)
    mcp_service_url: str = Field(..., description="URL do MCP App Service para este agente")
    report_fields: List[str] = Field(default_factory=list)
    report_mapping: Dict[str, str] = Field(default_factory=dict)

    def validate(self):
        if not self.mcp_service_url:
            raise ValueError("Campo 'mcp_service_url' é obrigatório para MCPAgentConfig.")
        if not self.agent_name:
            raise ValueError("Campo 'agent_name' é obrigatório para MCPAgentConfig.")
        if not self.mcp_url:
            raise ValueError("Campo 'mcp_url' é obrigatório para MCPAgentConfig.")

class MCPConfigRegistry(BaseModel):
    agents: Dict[str, MCPAgentConfig] = Field(default_factory=dict)
