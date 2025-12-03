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
    job_id: str

class MCPClientService:
    def __init__(self, base_url: str = None):
        # Remove a barra final se houver
        self.base_url = base_url or settings.MCP_SERVER_BASE_URL.rstrip('/')

    def get_mcp_endpoint(self, analysis_type: str) -> str:
        endpoint_dict = getattr(settings, 'MCP_ENDPOINTS', None)
        if not endpoint_dict or not isinstance(endpoint_dict, dict) or not endpoint_dict:
            # Se não houver endpoints específicos configurados, usa a base_url padrão
            return self.base_url
        return endpoint_dict.get(analysis_type, self.base_url)

    async def start_analysis(self, payload: MCPStartAnalysisPayload) -> MCPStartAnalysisResponse:
        # 1. Pega a configuração bruta
        raw_base = self.get_mcp_endpoint(payload.analysis_type)
        
        # --- LOG DE DEBUG FORENSE ---
        logging.info(f"🕵️ [DEBUG URL] Bruta vinda da env: '[{raw_base}]'")
        
        base = raw_base.strip().rstrip("/")
        url = f"{base}/start"
        
        logging.info(f"🔌 [MCP Client] URL Final Limpa: '[{url}]'")
    
        try:
            # 2. Compatibilidade Pydantic
            if hasattr(payload, "model_dump"):
                payload_dict = payload.model_dump()
            else:
                payload_dict = payload.dict()
    
            # 3. Requisição HTTP Real
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
                return MCPStartAnalysisResponse(**data)
    
        except httpx.HTTPStatusError as exc:
            raise Exception(f"Erro ao comunicar com MCP Server: {exc.response.status_code} - {exc.response.text}")
        except Exception as exc:
            logging.error(f"❌ [MCP Client] Falha ao chamar [{url}]: {str(exc)}", exc_info=True)
            raise Exception(f"Erro inesperado ao comunicar com MCP Server: {str(exc)}")
