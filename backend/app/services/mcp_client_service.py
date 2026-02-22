import json
import httpx
import logging

from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from backend.app.core.config import settings
from fastapi import UploadFile
from backend.app.utils.logging_utils import (
    log_service_call,
    log_error
)

class MCPStartAnalysisPayload(BaseModel):
    project_id: str = Field(...)
    job_id: str = Field(...)
    company_id: str = Field(...)
    group_ids: Optional[List[str]] = Field(default_factory=list)
    email: Optional[str] = Field(None)
    nome_projeto: Optional[str] = Field(None)
    analysis_type: Optional[str] = Field(None)
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
        log_service_call(
            service="MCPClientService",
            action="build_payload",
            payload=payload,
            job_id=payload.get("job_id"),
            project_id=payload.get("project_id")
        )
        raw_groups = payload.get("group_ids", [])
        group_ids_str = json.dumps(raw_groups) if isinstance(raw_groups, list) else raw_groups
        return {
            "project_id": payload.get("project_id"),
            "job_id": payload.get("job_id"),
            "company_id": payload.get("company_id"),
            "group_ids": group_ids_str,
            "email": payload.get("email"),
            "nome_projeto": payload.get("nome_projeto"),
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
        project_id = payload.get("project_id")
        company_id = payload.get("company_id")
        if not job_id:
            log_error(
                context="MCPClientService.start_analysis",
                error_message="job_id é obrigatório",
                exception=None,
                job_id=job_id,
                project_id=project_id
            )
            raise ValueError("job_id é obrigatório")

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
            log_service_call(
                service="MCPClientService",
                action="prepare_file",
                payload={"filename": arquivo_docx.filename, "content_type": arquivo_docx.content_type},
                job_id=job_id,
                project_id=project_id
            )

        try:
            log_service_call(
                service="MCPClientService",
                action="http_request",
                payload={"url": url, "method": "POST", "files": bool(files)},
                job_id=job_id,
                project_id=project_id
            )
            async with httpx.AsyncClient(timeout=120.0) as client:
                if files:
                    response = await client.post(url, data=data, files=files)
                else:
                    response = await client.post(url, data=data) 

                log_service_call(
                    service="MCPClientService",
                    action="http_response",
                    response={"status_code": response.status_code}, # Removi o body daqui para não poluir o log se o retorno for gigante
                    job_id=job_id,
                    project_id=project_id
                )
                response.raise_for_status()
                
                # O retorno não é estritamente necessário processar aqui se o Webhook já cuida do status
                # mas mantemos para evitar quebrar chamadores anteriores
                data_resp = response.json()
                return MCPStartAnalysisResponse(project_id=project_id, job_id=job_id)
                
        except Exception as exc:
            log_error(
                context="MCPClientService.start_analysis",
                error_message=f"Erro na comunicação com MCP: {str(exc)}",
                exception=exc,
                job_id=job_id,
                project_id=project_id
            )
            logging.error(f"❌ [MCP Client] Falha ao chamar [{url}]: {str(exc)}")
            raise Exception(f"Erro na comunicação com MCP: {str(exc)}")

    # MUDANÇA: Otimização do método de resgate do relatório para aceitar Markdown ou JSON
    async def get_report(self, project_id: str, job_id: str, mcp_url: str) -> Any:
        url = f"{mcp_url.rstrip('/')}/project/{project_id}/{job_id}/reports"
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                content_type = response.headers.get("content-type", "").lower()
                
                # Se o MCP responder com JSON {"conteudo": "..."}
                if "application/json" in content_type:
                    return response.json()
                # Se o MCP responder diretamente com o arquivo cru (Markdown/Texto)
                else:
                    return {"content": response.text}
                    
        except httpx.HTTPStatusError as exc:
            logging.error(f"Erro HTTP {exc.response.status_code} ao buscar relatório do MCP: {exc.response.text}")
            raise Exception(f"Falha ao obter relatório: Status {exc.response.status_code}")
        except Exception as exc:
            logging.error(f"Erro de conexão ao buscar relatório do MCP: {str(exc)}")
            raise Exception(f"Erro ao comunicar com o agente MCP: {str(exc)}")
