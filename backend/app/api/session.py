from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse
from backend.app.services.redis_session_service import RedisSessionService
import logging
import httpx
from backend.app.core.config import settings

router = APIRouter()
logger = logging.getLogger("session_api")

@router.get("/project/{project_id}/{job_id}/reports")
async def get_project_reports(
    project_id: str,
    job_id: str,
    email: str = Query(..., description="Email do usuário"),
    empresa: str = Query(..., description="Empresa do usuário")
):
    redis_service = RedisSessionService()
    report_data = redis_service.get_report_data_for_job(job_id)
    if report_data:
        return {
            "report_data": report_data,
            "job_id": job_id,
            "project_id": project_id
        }
    else:
        logger.info(f"Report data não encontrado para job_id {job_id}, retornando 202 (processando)")
        return JSONResponse(
            content={"status": "processing", "job_id": job_id, "project_id": project_id},
            status_code=status.HTTP_202_ACCEPTED
        )
