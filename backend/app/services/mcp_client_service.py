import httpx
from typing import Any, Dict
from pydantic import BaseModel
from app.core.config import settings

class MCPStartAnalysisPayload(BaseModel):
    analysis_type: str
    instrucoes_extras: str
    projeto: str
    analysis_name: str
    usuario_executor: str

class MCPStartAnalysisResponse(BaseModel):
    job_id: str

class MCPClientService:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.MCP_SERVER_BASE_URL.rstrip('/')

    async def start_analysis(self, payload: MCPStartAnalysisPayload) -> MCPStartAnalysisResponse:
        url = f"{self.base_url}/start-analysis"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    json=payload.dict(),
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                data = response.json()
                return MCPStartAnalysisResponse(**data)
        except httpx.HTTPStatusError as exc:
            raise Exception(f"Erro ao comunicar com MCP Server: {exc.response.status_code} - {exc.response.text}")
        except Exception as exc:
            raise Exception(f"Erro inesperado ao comunicar com MCP Server: {str(exc)}")
