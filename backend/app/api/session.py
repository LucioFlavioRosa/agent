from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Any, Dict
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.services.project_state_service import ProjectStateService
import logging

router = APIRouter()

class UpdateReportRequest(BaseModel):
    report_data: Dict[str, Any]

@router.get("/project/{project_id}/reports")
def get_project_reports(project_id: str):
    redis_service = RedisSessionService()
    logger = logging.getLogger("session_api")
    try:
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
        return reports
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Projeto não encontrado: {e}")

@router.put("/project/{project_id}/report")
def update_project_report(project_id: str, req: UpdateReportRequest):
    redis_service = RedisSessionService()
    logger = logging.getLogger("session_api")
    try:
        if not req.report_data or not isinstance(req.report_data, dict) or len(req.report_data) != 1:
            raise HTTPException(status_code=400, detail="report_data deve ser um dicionário com exatamente uma chave de relatório.")
        session_before = redis_service.get_session_by_project_id(project_id)
        logger.debug(f"[SESSION] Antes da atualização: {[getattr(session_before, rf, None) for rf in ['epicos_report','features_report','times_descricao_report','alocacao_times_report','premissas_riscos_report']]}")
        redis_service.update_report(project_id, req.report_data)
        session_after = redis_service.get_session_by_project_id(project_id)
        logger.debug(f"[SESSION] Depois da atualização: {[getattr(session_after, rf, None) for rf in ['epicos_report','features_report','times_descricao_report','alocacao_times_report','premissas_riscos_report']]}")
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(ProjectStateService.save_state_to_blob(session_after))
        else:
            loop.run_until_complete(ProjectStateService.save_state_to_blob(session_after))
        return {"status": "ok", "project_id": project_id, "nome_projeto": session_after.nome_projeto}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao atualizar relatório: {e}")

@router.post("/project/{project_id}/save-state")
async def save_project_state(project_id: str):
    redis_service = RedisSessionService()
    try:
        session = redis_service.get_session_by_project_id(project_id)
        url = await ProjectStateService.save_state_to_blob(session)
        return {"blob_url": url, "project_id": session.project_id, "nome_projeto": session.nome_projeto}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar estado: {e}")

@router.get("/project/{project_id}/docx-files")
def get_project_docx_files(project_id: str):
    redis_service = RedisSessionService()
    try:
        session = redis_service.get_session_by_project_id(project_id)
        return {"docx_files": session.docx_files, "project_id": session.project_id, "nome_projeto": session.nome_projeto}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Projeto não encontrado: {e}")
