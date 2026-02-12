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

    @staticmethod
    def validate_job_id(job_id):
        if not job_id or not isinstance(job_id, str) or not job_id.strip():
            raise ValueError('job_id é obrigatório e não pode ser vazio')
        return job_id

class MCPStartAnalysisResponse(BaseModel):
    project_id: str
    job_id: Optional[str] = None

class MCPClientService:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.MCP_SERVER_BASE_URL.rstrip('/')

    def _build_payload(self, payload: dict) -> dict:
        return {
            "project_id": payload.get("project_id"),
            "job_id": payload.get("job_id"),
            "email": payload.get("email"),
            "nome_projeto": payload.get("nome_projeto"),
            "agent_name": payload.get("agent_name"),
            "analysis_type": payload.get("analysis_type"),
            "branch": payload.get("branch"),
            "repository": payload.get("repository"),
            "comentario_extra": payload.get("comentario_extra")
        }

    async def start_analysis(
        self,
        payload: dict,
        mcp_service_url: str,
        arquivo_docx: Optional[UploadFile] = None
    ) -> MCPStartAnalysisResponse:
        base = mcp_service_url.strip().rstrip("/")
        url = f"{base}/start"
        
        job_id = payload.get("job_id")
        # Removi a chamada ao validador estático do Pydantic aqui para evitar conflitos
        if not job_id: raise ValueError("job_id é obrigatório")

        data = self._build_payload(payload)
        files = None

        if arquivo_docx is not None:
            
            await arquivo_docx.seek(0)
            
            files = {
                "arquivo_docx": (
                    arquivo_docx.filename,
                    arquivo_docx.file,
                    arquivo_docx.content_type or "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            }

        try:
            # Aumentei o timeout para 120s pois upload de arquivos + processamento de IA demora
            async with httpx.AsyncClient(timeout=120.0) as client:
                if files:
                    # Envio como multipart/form-data
                    response = await client.post(url, data=data, files=files)
                else:
                    # Envio como application/json
                    response = await client.post(url, json=data)

                response.raise_for_status()
                data_resp = response.json()
                
                return MCPStartAnalysisResponse(
                    project_id=data_resp.get("project_id", payload.get("project_id")),
                    job_id=data_resp.get("job_id", job_id)
                )
        except Exception as exc:
            logging.error(f"❌ [MCP Client] Falha ao chamar [{url}]: {str(exc)}")
            raise Exception(f"Erro na comunicação com MCP: {str(exc)}")
            
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
