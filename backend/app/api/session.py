from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.middleware.auth_middleware import get_current_user, _extract_usuario_executor
import logging

router = APIRouter()
logger = logging.getLogger("session_api")

@router.get("/project/{project_id}/{job_id}/reports")
async def get_project_reports(
    project_id: str,
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    redis_service = RedisSessionService()
    job = redis_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} não encontrado.")
    if job.status in ("pending", "in_progress"):
        return JSONResponse(
            content={
                "status": "processing",
                "message": "O processamento deste Job ainda está em andamento.",
                "job_id": job_id,
                "project_id": project_id
            },
            status_code=status.HTTP_202_ACCEPTED
        )
    if job.status == "done":
        report_data = redis_service.get_report_data_for_job(job_id)
        return report_data if report_data is not None else {}
    if job.status == "error":
        error_message = redis_service.get_error_message_for_job(job_id)
        raise HTTPException(status_code=500, detail=error_message or "Erro no processamento do Job.")
    raise HTTPException(status_code=404, detail=f"Status do Job {job_id} desconhecido.")
