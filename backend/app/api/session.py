from fastapi import APIRouter, HTTPException, Body, Depends, Request
from pydantic import BaseModel
from typing import Any, Dict
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.services.project_state_service import ProjectStateService
from backend.app.middleware.auth_middleware import get_current_user, _extract_usuario_executor
from backend.app.services.audit_service import AuditService
import logging

router = APIRouter()

class UpdateReportRequest(BaseModel):
    report_data: Dict[str, Any]

@router.get("/project/{project_id}/reports")
def get_project_reports(project_id: str, request: Request = None, current_user: dict = Depends(get_current_user)):
    redis_service = RedisSessionService()
    logger = logging.getLogger("session_api")
    usuario_executor = _extract_usuario_executor(current_user)
    try:
        if request is not None:
            try:
                AuditService.save_frontend_to_backend_payload(
                    payload={"project_id": project_id},
                    endpoint=f"/session/project/{project_id}/reports",
                    method="GET",
                    usuario_executor=usuario_executor,
                    project_id=project_id
                )
            except Exception as e:
                logger.error(f"Erro ao auditar payload frontend->backend em /session/project/{{project_id}}/reports: {e}")
        session = redis_service.get_session_by_project_id(project_id)
        state = session.to_project_state()
        state.pop("projeto", None)
        state.pop("comentario_usuario", None)
        state.pop("docx_blob_url", None)
        state.pop("extracted_text", None)
        report_fields = [
            "epicos_report",
            "features_report",
            "times_descricao_report",
            "alocacao_times_report",
            "premissas_riscos_report"
        ]
        normalized_count = 0
        for field in report_fields:
            if field not in state or state[field] is None or not isinstance(state[field], list):
                state[field] = []
                normalized_count += 1
        if normalized_count > 0:
            logger.debug(f"Normalização: {normalized_count} campos de relatório convertidos para lista em get_project_reports().")
        reports = {
            "epicos_report": state.get("epicos_report"),
            "features_report": state.get("features_report"),
            "times_descricao_report": state.get("times_descricao_report"),
            "alocacao_times_report": state.get("alocacao_times_report"),
            "premissas_riscos_report": state.get("premissas_riscos_report"),
            "project_id": state.get("project_id"),
            "nome_projeto": state.get("nome_projeto")
        }
        try:
            AuditService.save_backend_to_frontend_payload(
                response=reports,
                endpoint=f"/session/project/{project_id}/reports",
                status_code=200,
                usuario_executor=usuario_executor,
                project_id=project_id
            )
        except Exception as e:
            logger.error(f"Erro ao auditar payload backend->frontend em /session/project/{{project_id}}/reports: {e}")
        return reports
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Projeto não encontrado: {e}")

@router.put("/project/{project_id}/report")
def update_project_report(project_id: str, req: UpdateReportRequest, request: Request = None, current_user: dict = Depends(get_current_user)):
    redis_service = RedisSessionService()
    usuario_executor = _extract_usuario_executor(current_user)
    try:
        if request is not None:
            try:
                AuditService.save_frontend_to_backend_payload(
                    payload={"project_id": project_id, "report_data": req.report_data},
                    endpoint=f"/session/project/{project_id}/report",
                    method="PUT",
                    usuario_executor=usuario_executor,
                    project_id=project_id
                )
            except Exception as e:
                logging.getLogger("session_api").error(f"Erro ao auditar payload frontend->backend em /session/project/{{project_id}}/report: {e}")
        if not req.report_data or not isinstance(req.report_data, dict) or len(req.report_data) != 1:
            raise HTTPException(status_code=400, detail="report_data deve ser um dicionário com exatamente uma chave de relatório.")
        redis_service.update_report(project_id, req.report_data)
        session = redis_service.get_session_by_project_id(project_id)
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(ProjectStateService.save_state_to_blob(session))
        else:
            loop.run_until_complete(ProjectStateService.save_state_to_blob(session))
        response = {"status": "ok", "project_id": project_id, "nome_projeto": session.nome_projeto}
        try:
            AuditService.save_backend_to_frontend_payload(
                response=response,
                endpoint=f"/session/project/{project_id}/report",
                status_code=200,
                usuario_executor=usuario_executor,
                project_id=project_id
            )
        except Exception as e:
            logging.getLogger("session_api").error(f"Erro ao auditar payload backend->frontend em /session/project/{{project_id}}/report: {e}")
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao atualizar relatório: {e}")

@router.post("/project/{project_id}/save-state")
async def save_project_state(project_id: str, request: Request = None, current_user: dict = Depends(get_current_user)):
    redis_service = RedisSessionService()
    usuario_executor = _extract_usuario_executor(current_user)
    try:
        if request is not None:
            try:
                AuditService.save_frontend_to_backend_payload(
                    payload={"project_id": project_id},
                    endpoint=f"/session/project/{project_id}/save-state",
                    method="POST",
                    usuario_executor=usuario_executor,
                    project_id=project_id
                )
            except Exception as e:
                logging.getLogger("session_api").error(f"Erro ao auditar payload frontend->backend em /session/project/{{project_id}}/save-state: {e}")
        session = redis_service.get_session_by_project_id(project_id)
        url = await ProjectStateService.save_state_to_blob(session)
        response = {"blob_url": url, "project_id": session.project_id, "nome_projeto": session.nome_projeto}
        try:
            AuditService.save_backend_to_frontend_payload(
                response=response,
                endpoint=f"/session/project/{project_id}/save-state",
                status_code=200,
                usuario_executor=usuario_executor,
                project_id=project_id
            )
        except Exception as e:
            logging.getLogger("session_api").error(f"Erro ao auditar payload backend->frontend em /session/project/{{project_id}}/save-state: {e}")
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar estado: {e}")

@router.get("/project/{project_id}/docx-files")
def get_project_docx_files(project_id: str, request: Request = None, current_user: dict = Depends(get_current_user)):
    redis_service = RedisSessionService()
    usuario_executor = _extract_usuario_executor(current_user)
    try:
        if request is not None:
            try:
                AuditService.save_frontend_to_backend_payload(
                    payload={"project_id": project_id},
                    endpoint=f"/session/project/{project_id}/docx-files",
                    method="GET",
                    usuario_executor=usuario_executor,
                    project_id=project_id
                )
            except Exception as e:
                logging.getLogger("session_api").error(f"Erro ao auditar payload frontend->backend em /session/project/{{project_id}}/docx-files: {e}")
        session = redis_service.get_session_by_project_id(project_id)
        response = {"docx_files": session.docx_files, "project_id": session.project_id, "nome_projeto": session.nome_projeto}
        try:
            AuditService.save_backend_to_frontend_payload(
                response=response,
                endpoint=f"/session/project/{project_id}/docx-files",
                status_code=200,
                usuario_executor=usuario_executor,
                project_id=project_id
            )
        except Exception as e:
            logging.getLogger("session_api").error(f"Erro ao auditar payload backend->frontend em /session/project/{{project_id}}/docx-files: {e}")
        return response
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Projeto não encontrado: {e}")
