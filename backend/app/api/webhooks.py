import logging
from fastapi import APIRouter, HTTPException, status, Request, Depends
from backend.app.models.mcp_webhook_models import MCPWebhookPayload
from backend.app.services.redis_session_service import RedisSessionService

router = APIRouter()
logger = logging.getLogger("webhooks_api")

@router.post("/mcp", status_code=200, tags=["Webhooks"])
async def mcp_webhook(payload: MCPWebhookPayload, request: Request):
    redis_service = RedisSessionService()
    try:
        session = redis_service.get_session_by_job_id(payload.job_id)
        if not session:
            logger.error(f"Webhook recebido para job_id não encontrado: {payload.job_id}")
            raise HTTPException(status_code=404, detail=f"Sessão não encontrada para job_id: {payload.job_id}")
        analysis_type = getattr(session, "analysis_type", None)
        if payload.status in {"in_progress", "done"}:
            if not payload.report_type:
                logger.error(f"Webhook sem report_type para job_id {payload.job_id}")
                raise HTTPException(status_code=400, detail="report_type é obrigatório quando status é 'in_progress' ou 'done'")
            redis_service.update_report(
                session.session_id,
                payload.report_type,
                payload.report_data,
                analysis_type=analysis_type
            )
            logger.info(f"Relatório '{payload.report_type}' atualizado para sessão {session.session_id} (job_id={payload.job_id})")
        elif payload.status == "error":
            logger.error(f"Webhook de erro recebido: job_id={payload.job_id}, error_type={payload.error_type}, error_message={payload.error_message}")
        return {"status": "ok"}
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        logger.error(f"Erro ao processar webhook MCP: {exc}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar webhook MCP.")
