from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Any, Dict
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.services.project_state_service import ProjectStateService
import logging

router = APIRouter()
logger = logging.getLogger("session_api")

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
            "premissas_riscos_report": session.premissas_riscos_report
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Sessão não encontrada: {e}")

@router.put("/{session_id}/report")
def update_session_report(session_id: str, req: UpdateReportRequest):
    redis_service = RedisSessionService()
    try:
        logger.info(f"Atualizando relatório '{req.report_type}' na sessão {session_id} via substituição total da chave no dicionário reports.")
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(redis_service.update_report(session_id, req.report_type, req.report_data))
        redis_service.update_session_on_state_change(session_id, {})
        logger.info(f"Relatório '{req.report_type}' atualizado para sessão {session_id}.")
        # Salva imediatamente o estado atualizado no Blob Storage
        session_atualizada = redis_service.get_session(session_id)
        logger.info(f"Salvando estado atualizado no Blob Storage após update_report para session_id={session_id}")
        loop.run_until_complete(ProjectStateService.save_state_to_blob(session_atualizada))
        logger.info(f"Estado salvo imediatamente após atualização de relatório para sessão {session_id}")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao atualizar relatório: {e}")

@router.post("/{session_id}/save-state")
async def save_session_state(session_id: str):
    redis_service = RedisSessionService()
    try:
        session = redis_service.get_session(session_id)
        url = await ProjectStateService.save_state_to_blob(session)
        return {"blob_url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar estado: {e}")

@router.get("/{session_id}/docx-files")
def get_session_docx_files(session_id: str):
    redis_service = RedisSessionService()
    try:
        session = redis_service.get_session(session_id)
        return {"docx_files": session.docx_files}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Sessão não encontrada: {e}")
