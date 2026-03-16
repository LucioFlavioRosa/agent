import json
import httpx
import logging

from typing import Any, Dict, Optional, List
from fastapi import UploadFile
from backend.app.core.config import settings
from backend.app.utils.logging_utils import (
    log_service_call,
    log_error
)
from backend.app.models.mcp_models import MCPStartAnalysisPayload, MCPStartAnalysisResponse


class MCPClientService:
    def __init__(self, base_url: str = None):
        fallback_url = getattr(settings, 'MCP_SERVER_BASE_URL', '')
        self.base_url = base_url or fallback_url.rstrip('/') if fallback_url else ''

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
        
        raw_context = payload.get("context_used", {})
        context_used_str = json.dumps(raw_context) if raw_context else "{}"

        raw_data = {
            "project_id": payload.get("project_id"),
            "job_id": payload.get("job_id"),
            "company_id": payload.get("company_id"),
            "group_ids": group_ids_str,
            "email": payload.get("email"),
            "nome_projeto": payload.get("nome_projeto"),
            "analysis_type": payload.get("analysis_type"),
            "branch": payload.get("branch"),
            "repository": payload.get("repository"),
            "comentario_extra": payload.get("comentario_extra"),
            "context_used": context_used_str,
            "company_template": payload.get("company_template"),
            "target_epic_id": payload.get("target_epic_id")
        }
        
        # Retorna apenas chaves que possuem um valor real (evita mandar 'None' via form-data)
        return {k: v for k, v in raw_data.items() if v is not None}

    async def start_analysis(
        self,
        payload: dict,
        mcp_service_url: str,
        arquivo_docx: Optional[UploadFile] = None,
        arquivo_identidade: Optional[UploadFile] = None 
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
        files = {}

        if arquivo_docx is not None:
            await arquivo_docx.seek(0)
            file_bytes_docx = await arquivo_docx.read()
            files["arquivo_docx"] = (
                arquivo_docx.filename,
                file_bytes_docx,
                arquivo_docx.content_type or "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            log_service_call(
                service="MCPClientService",
                action="prepare_file_docx",
                payload={"filename": arquivo_docx.filename, "content_type": arquivo_docx.content_type},
                job_id=job_id,
                project_id=project_id
            )

        if arquivo_identidade is not None:
            await arquivo_identidade.seek(0)
            file_bytes_ident = await arquivo_identidade.read()
            files["arquivo_identidade"] = (
                arquivo_identidade.filename,
                file_bytes_ident,
                arquivo_identidade.content_type or "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            log_service_call(
                service="MCPClientService",
                action="prepare_file_identidade",
                payload={"filename": arquivo_identidade.filename, "content_type": arquivo_identidade.content_type},
                job_id=job_id,
                project_id=project_id
            )

        try:
            log_service_call(
                service="MCPClientService",
                action="http_request",
                payload={"url": url, "method": "POST", "files_count": len(files)},
                job_id=job_id,
                project_id=project_id
            )
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                if len(files) > 0:
                    response = await client.post(url, data=data, files=files)
                else:
                    response = await client.post(url, data=data) 

                log_service_call(
                    service="MCPClientService",
                    action="http_response",
                    response={"status_code": response.status_code}, 
                    job_id=job_id,
                    project_id=project_id
                )
                response.raise_for_status()
                
                return MCPStartAnalysisResponse(project_id=project_id, job_id=job_id)

        except httpx.HTTPStatusError as exc:
            erro_mcp = exc.response.text
            print(f"🚨 DETALHES DO ERRO 500 NO MCP: {erro_mcp}", flush=True)
            logging.error(f"Erro detalhado retornado pelo MCP: {erro_mcp}")
            raise Exception(f"O MCP recusou a requisição (500): {erro_mcp}")
        
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

    async def get_report(self, project_id: str, job_id: str, mcp_url: str, company_id: str, filename: str = "epics.md") -> Any:
        url = f"{mcp_url.rstrip('/')}/reports/{project_id}/{job_id}"
        
        params = {
            "company_id": company_id,
            "filename": filename
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                content_type = response.headers.get("content-type", "").lower()
                
                if "application/json" in content_type:
                    return response.json()
                else:
                    return {"report": response.text}
                    
        except httpx.HTTPStatusError as exc:
            erro_mcp = exc.response.text
            log_error(
                context="MCPClientService.get_report",
                error_message=f"Erro HTTP {exc.response.status_code} no MCP: {erro_mcp}",
                exception=exc, job_id=job_id, project_id=project_id
            )
            raise Exception(f"O agente MCP recusou a requisição ({exc.response.status_code}): {erro_mcp}")
        except Exception as exc:
            log_error(
                context="MCPClientService.get_report",
                error_message=f"Erro de conexão ao buscar relatório do MCP: {str(exc)}",
                exception=exc, job_id=job_id, project_id=project_id
            )
            logging.error(f"Erro de conexão ao buscar relatório do MCP: {str(exc)}")
            raise Exception(f"Erro ao comunicar com o agente MCP: {str(exc)}")
