import logging
import httpx
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, validator
from backend.app.core.config import settings
from fastapi.encoders import jsonable_encoder

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
    status: str
    session_id: str

class MCPClientService:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.MCP_SERVER_BASE_URL.rstrip('/')

    def get_mcp_endpoint(self, analysis_type: str) -> str:
        if (
            hasattr(settings, 'mcp_config_registry') and
            settings.mcp_config_registry and
            hasattr(settings.mcp_config_registry, 'agents') and
            analysis_type in settings.mcp_config_registry.agents
        ):
            agent_cfg = settings.mcp_config_registry.agents[analysis_type]
            if agent_cfg and agent_cfg.mcp_url:
                return agent_cfg.mcp_url.rstrip('/')
        return self.base_url

    async def start_analysis(self, payload: MCPStartAnalysisPayload) -> MCPStartAnalysisResponse:
        raw_base = self.get_mcp_endpoint(payload.analysis_type)
        logging.info(f"🕵️ [DEBUG URL] Bruta vinda da env: '[{raw_base}]'")
        base = raw_base.strip().rstrip("/")
        url = f"{base}/start"
        logging.info(f"🔌 [MCP Client] URL Final Limpa: '[{url}]'")
        try:
            if hasattr(payload, "model_dump"):
                payload_dict = payload.model_dump()
            else:
                payload_dict = payload.dict()
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    url,
                    json=jsonable_encoder(payload_dict), 
                    headers={"Content-Type": "application/json"}
                )
                if response.status_code != 200:
                    logging.error(f"❌ [MCP Client] Erro {response.status_code}: {response.text}")
                response.raise_for_status()
                data = response.json()
                if data.get('session_id') != payload.session_id:
                    raise Exception(f"O MCP retornou um session_id diferente do enviado. Esperado: {payload.session_id}, Recebido: {data.get('session_id')}")
                return MCPStartAnalysisResponse(**data)
        except httpx.HTTPStatusError as exc:
            raise Exception(f"Erro ao comunicar com MCP Server: {exc.response.status_code} - {exc.response.text}")
        except Exception as exc:
            logging.error(f"❌ [MCP Client] Falha ao chamar [{url}]: {str(exc)}", exc_info=True)
            raise Exception(f"Erro inesperado ao comunicar com MCP Server: {str(exc)}")
