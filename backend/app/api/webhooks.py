import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, status
from backend.app.services.redis_session_service import RedisSessionService

router = APIRouter()
logger = logging.getLogger("webhooks_api")

@router.post("/mcp", status_code=status.HTTP_200_OK, tags=["Webhooks"])
async def mcp_webhook(payload: dict, request: Request):
    # Extração dos dados
    job_id = payload.get("job_id")
    project_id = payload.get("project_id")
    company_id_recebido = payload.get("company_id")
    status_val = payload.get("status")
    report_data = payload.get("report_data")
    error_message = payload.get("error_message")

    logger.info(f"[Webhook] Recebido do MCP: job_id={job_id}, status={status_val}, company_id={company_id_recebido}")

    # 1. Validação Criteriosa (Fail Fast)
    required_fields = [job_id, project_id, status_val, company_id_recebido]
    if not all(required_fields):
        logger.error(f"[Webhook] Payload incompleto: {payload}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Campos obrigatórios ausentes: job_id, project_id, status e company_id."
        )
    redis_service = RedisSessionService()

    try:
        # 2. Atualização de Status
        redis_service.update_job_status(job_id, status_val)
        msg = f"Job {job_id} atualizado para {status_val}"

        # 3. Armazenamento com "Carimbo" de Empresa
        if status_val == "done" and report_data is not None:
            enriched_report = {
                "content": report_data,
                "company_id": company_id_recebido, # Vínculo de segurança
                "finalized_at": datetime.utcnow().isoformat(),
                "project_id": project_id
            }
            redis_service.store_report_data_for_job(job_id, enriched_report)
            msg += " - relatório armazenado com vínculo de empresa."

        elif status_val == "error":
            err_msg = error_message or "Erro desconhecido processado pelo MCP."
            redis_service.store_error_message_for_job(job_id, err_msg)
            msg += " - erro registrado."

        logger.info(f"[Webhook] Finalizado com sucesso: {msg}")
        return {
            "status": "ok", 
            "job_id": job_id, 
            "msg": msg
        }

    except Exception as e:
        logger.error(f"[Webhook] Erro ao processar Redis para job {job_id}: {str(e)}")
        # Retornamos 500 para sinalizar ao MCP que o servidor está com problemas e ele pode tentar o retry
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Erro interno ao persistir dados do webhook."
        )
