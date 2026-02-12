import logging
from fastapi import APIRouter, HTTPException, Request
from backend.app.services.redis_session_service import RedisSessionService

router = APIRouter()
logger = logging.getLogger("webhooks_api")

@router.post("/mcp", status_code=200, tags=["Webhooks"])
async def mcp_webhook(payload: dict, request: Request):
    job_id = payload.get("job_id")
    project_id = payload.get("project_id")
    status_val = payload.get("status")
    report_data = payload.get("report_data")
    error_message = payload.get("error_message")

    logger.info(f"[Webhook] Recebido payload do MCP: job_id={job_id}, project_id={project_id}, status={status_val}")
    redis_service = RedisSessionService()

    # Validação dos campos obrigatórios
    if not project_id or not job_id or not status_val:
        logger.error(f"[Webhook] Campos obrigatórios ausentes: project_id={project_id}, job_id={job_id}, status={status_val}")
        raise HTTPException(status_code=400, detail="Campos obrigatórios ausentes: project_id, job_id, status.")

    # Atualiza status do job no Redis
    try:
        logger.info(f"[Webhook] Atualizando status no Redis: job_id={job_id}, status={status_val}")
        redis_service.update_job_status(job_id, status_val)
    except Exception as e:
        logger.error(f"[Webhook] Falha ao atualizar status no Redis para job_id={job_id}: {e}")

    msg = f"Job {job_id} status: {status_val}"

    # Armazenamento de report_data
    if status_val == "done" and report_data is not None:
        try:
            logger.info(f"[Webhook] Armazenando report_data para job_id={job_id}")
            redis_service.store_report_data_for_job(job_id, report_data)
            msg += " - report_data armazenado."
        except Exception as e:
            logger.error(f"[Webhook] Falha ao armazenar report_data para job_id={job_id}: {e}")

    # Armazenamento de error_message
    if status_val == "error" and error_message is not None:
        try:
            logger.info(f"[Webhook] Armazenando error_message para job_id={job_id}: {error_message}")
            redis_service.store_error_message_for_job(job_id, error_message)
            msg += f" - error_message armazenado: {error_message}"
        except Exception as e:
            logger.error(f"[Webhook] Falha ao armazenar error_message para job_id={job_id}: {e}")

    logger.info(f"[Webhook] Resposta final enviada para job_id={job_id}, project_id={project_id}, msg={msg}")
    return {"status": "ok", "project_id": project_id, "job_id": job_id, "msg": msg}
