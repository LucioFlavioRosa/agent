import httpx
from typing import Any, Dict
from pydantic import BaseModel
from app.core.config import settings

class MCPStartAnalysisPayload(BaseModel):
    analysis_type: str
    instrucoes_extras: str = None
    projeto: str
    analysis_name: str
    usuario_executor: str
    session_id: str

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
            if payload_dict.get('instrucoes_extras', None) is None:
                payload_dict.pop('instrucoes_extras', None)
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
