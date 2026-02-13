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
    logger.info(f"[Session] Requisição: project_id={project_id}, job_id={job_id}, email={email}, empresa={empresa}")

    # --- VALIDAÇÕES ORIGINAIS REINTEGRADAS (Críticas para Estabilidade) ---
    if not project_id or not isinstance(project_id, str) or not project_id.strip():
        logger.error(f"[Session] project_id inválido ou ausente: {project_id}")
        raise HTTPException(status_code=400, detail="project_id inválido ou ausente.")
        
    if not job_id or not isinstance(job_id, str) or not job_id.strip():
        logger.error(f"[Session] job_id inválido ou ausente: {job_id}")
        raise HTTPException(status_code=400, detail="job_id inválido ou ausente.")

    # --- LÓGICA DE NEGÓCIO E SEGURANÇA MULTI-TENANT ---
    redis_service = RedisSessionService()
    
    logger.info(f"[Session] Buscando envelope no Redis para job_id={job_id}")
    envelope = redis_service.get_report_data_for_job(job_id)

    if envelope:
        # Validação de Ownership (Segurança)
        company_owner = envelope.get("company_id")
        
        if company_owner and company_owner != empresa:
            logger.error(f"[Session] ACESSO NEGADO: {email} ({empresa}) tentou ler job de {company_owner}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Acesso negado: Este relatório pertence a outra organização."
            )

        logger.info(f"[Session] Sucesso: Relatório liberado.")
        return JSONResponse(
            content={
                "report_data": envelope.get("content"), # Extraímos apenas o conteúdo
                "job_id": job_id,
                "project_id": project_id,
                "status": "success"
            },
            status_code=status.HTTP_200_OK
        )

    else:
        # Verifica se há erro registrado no Redis para este job
        error_msg = redis_service.get_error_message_for_job(job_id)
        if error_msg:
            return JSONResponse(
                content={"status": "error", "message": error_msg, "job_id": job_id},
                status_code=status.HTTP_200_OK
            )

        logger.info(f"[Session] Job {job_id} ainda em processamento.")
        return JSONResponse(
            content={
                "status": "processing",
                "job_id": job_id,
                "project_id": project_id,
                "message": "O relatório ainda está sendo processado pelo MCP."
            },
            status_code=status.HTTP_202_ACCEPTED
        )
