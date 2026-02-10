import logging
from fastapi import APIRouter, HTTPException, Request
from backend.app.services.redis_session_service import RedisSessionService

router = APIRouter()
logger = logging.getLogger("webhooks_api")

@router.post("/mcp", status_code=200, tags=["Webhooks"])
async def mcp_webhook(payload: dict, request: Request):
    redis_service = RedisSessionService()
    project_id = payload.get("project_id")
    job_id = payload.get("job_id")
    status_val = payload.get("status")
    report_data = payload.get("report_data")
    error_message = payload.get("error_message")

    # Validação dos campos obrigatórios
    if not project_id or not job_id or not status_val:
        raise HTTPException(status_code=400, detail="Campos obrigatórios ausentes: project_id, job_id, status.")

    # Atualiza status do job no Redis
    redis_service.update_job_status(job_id, status_val)

    msg = f"Job {job_id} status: {status_val}"
    if status_val == "done" and report_data is not None:
        redis_service.store_report_data_for_job(job_id, report_data)
        msg += " - report_data armazenado."
    if status_val == "error" and error_message is not None:
        redis_service.store_error_message_for_job(job_id, error_message)
        msg += f" - error_message armazenado: {error_message}"

    return {"status": "ok", "project_id": project_id, "job_id": job_id, "msg": msg}
