import logging
from fastapi import APIRouter, HTTPException, Request
from backend.app.services.redis_session_service import RedisSessionService

router = APIRouter()
logger = logging.getLogger("webhooks_api")

@router.post("/mcp", status_code=200, tags=["Webhooks"])
async def mcp_webhook(payload: dict, request: Request):
    redis_service = RedisSessionService()
    job_id = payload.get("job_id")
    status_val = payload.get("status")
    project_id = payload.get("project_id")
    report_data = payload.get("report_data")
    error_message = payload.get("error_message")

    if not job_id or not status_val or not project_id:
        raise HTTPException(status_code=400, detail="Campos obrigatórios ausentes: job_id, status, project_id.")
    redis_service.update_job_status(job_id, status_val)
    if report_data is not None:
        redis_service.store_report_data_for_job(job_id, report_data)
    if status_val == "error" and error_message is not None:
        redis_service.store_error_message_for_job(job_id, error_message)
    return {"status": "ok", "project_id": project_id}
