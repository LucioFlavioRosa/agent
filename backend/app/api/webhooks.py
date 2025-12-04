import logging
from fastapi import APIRouter, HTTPException, status, Request, Depends
from backend.app.models.mcp_webhook_models import MCPWebhookPayload
from backend.app.services.redis_session_service import RedisSessionService
from backend.app.utils.webhook_validator import validate_report_data_structure

router = APIRouter()
logger = logging.getLogger("webhooks_api")

@router.post("/mcp", status_code=200, tags=["Webhooks"])
async def mcp_webhook(payload: MCPWebhookPayload, request: Request):
    redis_service = RedisSessionService()
    logger.info(f"Recebido webhook MCP para job_id: {payload.job_id}, status: {payload.status}")
    try:
        logger.info(f"Buscando sessão associada ao job_id: {payload.job_id}")
        session = redis_service.get_session_by_job_id(payload.job_id)
        if not session:
            logger.error(f"Webhook recebido para job_id não encontrado: {payload.job_id}. Estado do Redis pode estar inconsistente.")
            raise HTTPException(status_code=404, detail=f"Sessão não encontrada para job_id: {payload.job_id}")
        analysis_type = getattr(session, "analysis_type", None)
        if payload.status in {"in_progress", "done"}:
            if not payload.report_type:
                logger.error(f"Webhook sem report_type para job_id {payload.job_id}")
                raise HTTPException(status_code=400, detail="report_type é obrigatório quando status é 'in_progress' ou 'done'")
            if not validate_report_data_structure(payload.report_type, payload.report_data, analysis_type):
                logger.error(f"Estrutura de report_data inválida para report_type '{payload.report_type}', analysis_type '{analysis_type}' e job_id '{payload.job_id}'")
                raise HTTPException(status_code=400, detail=f"Estrutura de report_data inválida para report_type '{payload.report_type}' e analysis_type '{analysis_type}'")
            logger.info(f"Atualizando relatório '{payload.report_type}' na sessão {session.session_id} via substituição total da chave no dicionário reports.")
            await redis_service.update_report(
                session.session_id,
                payload.report_type,
                payload.report_data,
                analysis_type=analysis_type
            )
            try:
                session_atualizada = redis_service.get_session(session.session_id)
                from backend.app.services.project_state_service import ProjectStateService
                await ProjectStateService.save_state_to_blob(session_atualizada)
                logger.info(f"Estado salvo imediatamente após atualização de relatório para sessão {session.session_id} (job_id={payload.job_id})")
            except Exception as e:
                logger.error(f"Erro ao salvar estado imediato no Blob após webhook MCP: {e}")
            logger.info(f"Relatório '{payload.report_type}' atualizado para sessão {session.session_id} (job_id={payload.job_id})")
        elif payload.status == "error":
            logger.error(f"Webhook de erro recebido: job_id={payload.job_id}, error_type={payload.error_type}, error_message={payload.error_message}")
        return {"status": "ok"}
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        logger.error(f"Erro ao processar webhook MCP: {exc}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar webhook MCP.")
