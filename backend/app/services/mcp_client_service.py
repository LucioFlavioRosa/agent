import logging
import httpx
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from backend.app.core.config import settings
from fastapi import UploadFile

class MCPStartAnalysisPayload(BaseModel):
    project_id: str = Field(...)
    job_id: str = Field(...)
    email: Optional[str] = Field(None)
    nome_projeto: Optional[str] = Field(None)
    agent_name: Optional[str] = Field(None)
    branch: Optional[str] = Field(None)
    repository: Optional[str] = Field(None)
    comentario_extra: Optional[str] = Field(None)
    instrucoes_extras: Optional[str] = Field(None)
    # arquivo_docx não é processado, apenas repassado

class MCPStartAnalysisResponse(BaseModel):
    project_id: str
    job_id: Optional[str] = None

class MCPClientService:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.MCP_SERVER_BASE_URL.rstrip('/')

    async def start_analysis(
        self,
        payload: dict,
        mcp_service_url: str,
        arquivo_docx: Optional[UploadFile] = None
    ) -> MCPStartAnalysisResponse:
        base = mcp_service_url.strip().rstrip("/")
        url = f"{base}/start"
        logging.info(f"🔌 [MCP Client] URL Final Limpa: '[{url}]'")

        # Monta dados para envio
        data = {
            "project_id": payload.get("project_id"),
            "job_id": payload.get("job_id"),
            "email": payload.get("email"),
            "nome_projeto": payload.get("nome_projeto"),
            "agent_name": payload.get("agent_name"),
            "analysis_type": payload.get("analysis_type"),
            "branch": payload.get("branch"),
            "repository": payload.get("repository"),
            "comentario_extra": payload.get("comentario_extra"),
            "instrucoes_extras": payload.get("instrucoes_extras")
        }

        files = None
        if arquivo_docx is not None:
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
                    raise Exception(f"Erro ao comunicar com MCP Server: {response.status_code} - {response.text}")
                data_resp = response.json()
                return MCPStartAnalysisResponse(
                    project_id=data_resp.get("project_id", payload.get("project_id")),
                    job_id=data_resp.get("job_id", payload.get("job_id"))
                )
        except httpx.HTTPStatusError as exc:
            raise Exception(f"Erro ao comunicar com MCP Server: {exc.response.status_code} - {exc.response.text}")
        except Exception as exc:
            logging.error(f"❌ [MCP Client] Falha ao chamar [{url}]: {str(exc)}", exc_info=True)
            raise Exception(f"Erro inesperado ao comunicar com MCP Server: {str(exc)}")

    async def get_projects(self, email: str, empresa: str, mcp_url: str) -> Any:
        url = f"{mcp_url.rstrip('/')}/projects/list"
        payload = {
            "email": email,
            "empresa": empresa
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            logging.error(f"Erro ao buscar projetos do MCP: {str(exc)}")
            raise Exception(f"Erro ao buscar projetos do MCP: {str(exc)}")

    async def get_report(self, project_id: str, job_id: str, mcp_url: str) -> Any:
        url = f"{mcp_url.rstrip('/')}/project/{project_id}/{job_id}/reports"
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            logging.error(f"Erro ao buscar relatório do MCP: {str(exc)}")
            raise Exception(f"Erro ao buscar relatório do MCP: {str(exc)}")
