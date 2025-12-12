import logging
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Request
from backend.app.models.mcp_webhook_models import MCPWebhookPayload
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.services.project_state_service import ProjectStateService

router = APIRouter()
logger = logging.getLogger("webhooks_api")

@router.post("/mcp", status_code=200, tags=["Webhooks"])
async def mcp_webhook(payload: MCPWebhookPayload, request: Request):
    redis_service = RedisSessionService()
    logger.info(f"webhook_start: job_id={payload.job_id}, status={payload.status}")
    try:
        if not getattr(payload, 'project_id', None):
            raise HTTPException(status_code=400, detail="project_id é obrigatório.")
        if payload.status == "in_progress":
            redis_service.update_job_status(payload.job_id, "in_progress")
            return {"status": "ok", "msg": "Job marcado como in_progress"}
        if payload.status == "error":
            redis_service.update_job_status(payload.job_id, "error")
            logger.error(f"Job falhou: {payload.error_message}")
            return {"status": "ok", "msg": "Job marcado como error"}
        if payload.status == "done":
            report_data = payload.report_data
            if not report_data or not isinstance(report_data, dict):
                raise HTTPException(status_code=400, detail="report_data inválido")
            redis_service.update_report(payload.project_id, report_data)
            redis_service.update_job_status(payload.job_id, "done")
            session = redis_service.get_session_by_project_id(payload.project_id)
            if session:
                agora_iso = datetime.utcnow().isoformat()
                if hasattr(session, "ultima_atualizacao"):
                    session.ultima_atualizacao = agora_iso
                if hasattr(session, "last_saved_to_blob"):
                    session.last_saved_to_blob = agora_iso
                if isinstance(session, dict):
                    session["ultima_atualizacao"] = agora_iso
                    session["last_saved_to_blob"] = agora_iso
                if hasattr(session, "project_id") and not session.project_id:
                    session.project_id = payload.project_id
                await ProjectStateService.save_state_to_blob(session)
            logger.info(f"Job {payload.job_id} finalizado e marcado como DONE no Redis.")
            return {"status": "ok", "project_id": payload.project_id}
    except Exception as e:
        logger.error(f"Erro crítico no webhook: {e}")
        try:
            redis_service.update_job_status(payload.job_id, "error")
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e))
