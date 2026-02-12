from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.models.job_models import JobData
import logging

router = APIRouter()
logger = logging.getLogger("session_api")

@router.get("/project/{project_id}/{job_id}/reports")
async def get_project_reports(
    project_id: str,
    job_id: str,
    email: str = Query(..., description="Email do usuário"),
    empresa: str = Query(..., description="Empresa do usuário")
):
    logger.info(f"[Session] Recebida requisição para /project/{project_id}/{job_id}/reports com project_id={project_id}, job_id={job_id}, email={email}, empresa={empresa}")
    # Validação mínima dos IDs
    if not project_id or not isinstance(project_id, str) or not project_id.strip():
        logger.error(f"[Session] project_id inválido ou ausente: {project_id}")
        raise HTTPException(status_code=400, detail="project_id inválido ou ausente.")
    if not job_id or not isinstance(job_id, str) or not job_id.strip():
        logger.error(f"[Session] job_id inválido ou ausente: {job_id}")
        raise HTTPException(status_code=400, detail="job_id inválido ou ausente.")

    redis_service = RedisSessionService()
    logger.info(f"[Session] Buscando report_data no Redis para job_id={job_id}")
    report_data = redis_service.get_report_data_for_job(job_id)
    if report_data:
        logger.info(f"[Session] report_data encontrado para job_id={job_id}. Retornando status 200.")
        response = JSONResponse(
            content={
                "report_data": report_data,
                "job_id": job_id,
                "project_id": project_id
            },
            status_code=status.HTTP_200_OK
        )
    else:
        logger.info(f"[Session] report_data NÃO encontrado para job_id={job_id}. Retornando status 202 (processando).")
        response = JSONResponse(
            content={
                "status": "processing",
                "job_id": job_id,
                "project_id": project_id,
                "message": "O relatório ainda está sendo processado pelo MCP."
            },
            status_code=status.HTTP_202_ACCEPTED
        )
    logger.info(f"[Session] Resposta final enviada para job_id={job_id}, project_id={project_id}, status={response.status_code}")
    return response
