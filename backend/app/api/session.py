from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Any, Dict
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.services.project_state_service import ProjectStateService

router = APIRouter()

class UpdateReportRequest(BaseModel):
    report_type: str
    report_data: Any

@router.get("/session/{session_id}/reports")
def get_session_reports(session_id: str):
    redis_service = RedisSessionService()
    try:
        session = redis_service.get_session(session_id)
        return {
            "epicos_report": session.epicos_report,
            "features_report": session.features_report,
            "times_descricao_report": session.times_descricao_report,
            "alocacao_times_report": session.alocacao_times_report,
            "premissas_riscos_report": session.premissas_riscos_report
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Sessão não encontrada: {e}")

@router.put("/session/{session_id}/report")
def update_session_report(session_id: str, req: UpdateReportRequest):
    redis_service = RedisSessionService()
    try:
        redis_service.update_report(session_id, req.report_type, req.report_data)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao atualizar relatório: {e}")

@router.post("/session/{session_id}/save-state")
async def save_session_state(session_id: str):
    redis_service = RedisSessionService()
    try:
        session = redis_service.get_session(session_id)
        url = await ProjectStateService.save_state_to_blob(session)
        return {"blob_url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar estado: {e}")

@router.get("/session/{session_id}/docx-files")
def get_session_docx_files(session_id: str):
    redis_service = RedisSessionService()
    try:
        session = redis_service.get_session(session_id)
        return {"docx_files": session.docx_files}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Sessão não encontrada: {e}")
