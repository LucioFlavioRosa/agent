import httpx
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, validator
from backend.app.core.config import settings

class MCPStartAnalysisPayload(BaseModel):
    projeto: str = Field(...)
    analysis_type: str = Field(...)
    arquivo_docx: Optional[str] = Field(None)
    comentario_usuario: Optional[str] = Field(None)
    usuario_executor: str = Field(...)
    session_id: str = Field(...)

    @validator('analysis_type')
    def analysis_type_must_not_be_empty(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError('analysis_type deve ser uma string não vazia')
        return v

class MCPStartAnalysisResponse(BaseModel):
    job_id: str

class MCPClientService:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.MCP_SERVER_BASE_URL.rstrip('/')

    def get_mcp_endpoint(self, analysis_type: str) -> str:
        endpoint_dict = getattr(settings, 'MCP_ENDPOINTS', None)
        if not endpoint_dict or not isinstance(endpoint_dict, dict) or not endpoint_dict:
            raise ValueError("O mapeamento de endpoints MCP (settings.MCP_ENDPOINTS) não está configurado ou está vazio.")
        return endpoint_dict.get(analysis_type, self.base_url)

    async def start_analysis(self, payload: MCPStartAnalysisPayload) -> MCPStartAnalysisResponse:
        url = f"{self.get_mcp_endpoint(payload.analysis_type)}/start-analysis"
        try:
            payload_dict = payload.dict()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    json=payload_dict,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                data = response.json()
                return MCPStartAnalysisResponse(**data)
        except httpx.HTTPStatusError as exc:
            raise Exception(f"Erro ao comunicar com MCP Server: {exc.response.status_code} - {exc.response.text}")
        except Exception as exc:
            raise Exception(f"Erro inesperado ao comunicar com MCP Server: {str(exc)}")
