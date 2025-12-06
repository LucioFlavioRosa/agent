from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Any, Dict
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.services.project_state_service import ProjectStateService

router = APIRouter()

class UpdateReportRequest(BaseModel):
    report_type: str
    report_data: Any

@router.get("/{session_id}/reports")
def get_session_reports(session_id: str):
    redis_service = RedisSessionService()
    try:
        session = redis_service.get_session(session_id)
        return {
            "epicos_report": session.epicos_report,
            "features_report": session.features_report,
            "times_descricao_report": session.times_descricao_report,
            "alocacao_times_report": session.alocacao_times_report,
            "premissas_riscos_report": session.premissas_riscos_report,
            "project_id": session.project_id,
            "nome_projeto": session.projeto
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Sessão não encontrada: {e}")

@router.put("/{session_id}/report")
def update_session_report(session_id: str, req: UpdateReportRequest):
    redis_service = RedisSessionService()
    try:
        session = redis_service.get_session(session_id)
        project_id = session.project_id
        redis_service.update_report(session_id, req.report_type, req.report_data, analysis_type=session.analysis_type)
        redis_service.update_session_on_state_change(session_id, {})
        return {"status": "ok", "project_id": project_id, "nome_projeto": session.projeto}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao atualizar relatório: {e}")

@router.post("/{session_id}/save-state")
async def save_session_state(session_id: str):
    redis_service = RedisSessionService()
    try:
        session = redis_service.get_session(session_id)
        url = await ProjectStateService.save_state_to_blob(session)
        return {"blob_url": url, "project_id": session.project_id, "nome_projeto": session.projeto}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar estado: {e}")

@router.get("/{session_id}/docx-files")
def get_session_docx_files(session_id: str):
    redis_service = RedisSessionService()
    try:
        session = redis_service.get_session(session_id)
        return {"docx_files": session.docx_files, "project_id": session.project_id, "nome_projeto": session.projeto}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Sessão não encontrada: {e}")
