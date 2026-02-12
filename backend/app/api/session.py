from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.models.job_models import JobData
import logging
from backend.app.utils import logger_utils

router = APIRouter()
logger = logging.getLogger("session_api")

@router.get("/project/{project_id}/{job_id}/reports")
async def get_project_reports(
    project_id: str,
    job_id: str,
    email: str = Query(..., description="Email do usuário"),
    empresa: str = Query(..., description="Empresa do usuário")
):
    logger_utils.log_request_received(logger, "get_project_reports", {
        "project_id": project_id,
        "job_id": job_id,
        "email": email,
        "empresa": empresa
    })
    # Validação mínima dos IDs
    logger_utils.log_validation_step(logger, "get_project_reports", "Validando project_id e job_id")
    if not project_id or not isinstance(project_id, str) or not project_id.strip():
        logger_utils.log_validation_step(logger, "get_project_reports", "project_id inválido ou ausente")
        raise HTTPException(status_code=400, detail="project_id inválido ou ausente.")
    if not job_id or not isinstance(job_id, str) or not job_id.strip():
        logger_utils.log_validation_step(logger, "get_project_reports", "job_id inválido ou ausente")
        raise HTTPException(status_code=400, detail="job_id inválido ou ausente.")

    redis_service = RedisSessionService()
    logger_utils.log_service_call(logger, "get_project_reports", "Buscando report_data no Redis", {"job_id": job_id})
    report_data = redis_service.get_report_data_for_job(job_id)
    if report_data:
        logger_utils.log_response_sent(logger, "get_project_reports", "Retornando report_data (200)", {"job_id": job_id, "project_id": project_id})
        return JSONResponse(
            content={
                "report_data": report_data,
                "job_id": job_id,
                "project_id": project_id
            },
            status_code=status.HTTP_200_OK
        )
    else:
        logger_utils.log_response_sent(logger, "get_project_reports", "Report data não encontrado, retornando 202 (processando)", {"job_id": job_id, "project_id": project_id})
        return JSONResponse(
            content={
                "status": "processing",
                "job_id": job_id,
                "project_id": project_id,
                "message": "O relatório ainda está sendo processado pelo MCP."
            },
            status_code=status.HTTP_202_ACCEPTED
        )
