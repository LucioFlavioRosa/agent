import logging
import httpx
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from backend.app.core.config import settings
from fastapi import UploadFile

class MCPStartAnalysisPayload(BaseModel):
    project_id: str = Field(...)
    comentario_extra: Optional[str] = Field(None)
    analysis_type: str = Field(...)
    job_id: str = Field(...)
    # arquivo_docx não é processado, apenas repassado

class MCPStartAnalysisResponse(BaseModel):
    project_id: str

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

    async def start_analysis(self, payload: dict, arquivo_docx: Optional[UploadFile] = None) -> MCPStartAnalysisResponse:
        raw_base = self.get_mcp_endpoint(payload["analysis_type"])
        logging.info(f"🕵️ [DEBUG URL] Bruta vinda da env: '[{raw_base}]'")
        base = raw_base.strip().rstrip("/")
        url = f"{base}/start"
        logging.info(f"🔌 [MCP Client] URL Final Limpa: '[{url}]'")

        # Monta dados para envio
        data = {
            "project_id": payload["project_id"],
            "comentario_extra": payload.get("comentario_extra"),
            "analysis_type": payload["analysis_type"],
            "job_id": payload["job_id"]
        }

        files = None
        if arquivo_docx is not None:
            # Não processa nem lê o arquivo, apenas repassa como multipart
            files = {
                "arquivo_docx": (arquivo_docx.filename, arquivo_docx.file, arquivo_docx.content_type or "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                if files:
                    response = await client.post(
                        url,
                        data=data,
                        files=files
                    )
                else:
                    response = await client.post(
                        url,
                        json=data,
                        headers={"Content-Type": "application/json"}
                    )
                if response.status_code != 200:
                    logging.error(f"❌ [MCP Client] Erro {response.status_code}: {response.text}")
                response.raise_for_status()
                data_resp = response.json()
                return MCPStartAnalysisResponse(project_id=data_resp.get("project_id", payload["project_id"]))
        except httpx.HTTPStatusError as exc:
            raise Exception(f"Erro ao comunicar com MCP Server: {exc.response.status_code} - {exc.response.text}")
        except Exception as exc:
            logging.error(f"❌ [MCP Client] Falha ao chamar [{url}]: {str(exc)}", exc_info=True)
            raise Exception(f"Erro inesperado ao comunicar com MCP Server: {str(exc)}")
