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
            await redis_service.update_report(
                session.session_id,
                payload.report_type,
                payload.report_data,
                analysis_type=analysis_type
            )
            try:
                session_atualizada = redis_service.get_session(session.session_id)
                analysis_type_atualizada = getattr(session_atualizada, "analysis_type", None)
                report_field = None
                if hasattr(redis_service, "logger"):
                    redis_service.logger.debug(f"Validação pós-update_report: session_id={session.session_id}, analysis_type={analysis_type_atualizada}")
                if hasattr(redis_service, "get_session") and hasattr(session_atualizada, "reports"):
                    if hasattr(settings, "mcp_config_registry") and settings.mcp_config_registry and hasattr(settings.mcp_config_registry, "agents") and analysis_type_atualizada in settings.mcp_config_registry.agents:
                        agent_cfg = settings.mcp_config_registry.agents[analysis_type_atualizada]
                        if hasattr(agent_cfg, "report_mapping") and payload.report_type in agent_cfg.report_mapping:
                            report_field = agent_cfg.report_mapping[payload.report_type]
                        else:
                            report_field = f"{payload.report_type}_report"
                    else:
                        report_field = f"{payload.report_type}_report"
                    valor_armazenado = session_atualizada.reports.get(report_field)
                    if valor_armazenado != payload.report_data:
                        logger.critical(f"Falha crítica: O relatório armazenado ('{report_field}') não corresponde ao report_data recebido do MCP para session_id={session.session_id}. Valor armazenado: {valor_armazenado} | Valor recebido: {payload.report_data}")
                        raise HTTPException(status_code=500, detail="Falha ao atualizar relatório: valor armazenado difere do valor recebido.")
            except Exception as e:
                logger.error(f"Erro na validação pós-update_report: {e}")
                raise HTTPException(status_code=500, detail=f"Erro interno ao validar atualização do relatório: {e}")
            logger.info(f"Relatório '{payload.report_type}' atualizado para sessão {session.session_id} (job_id={payload.job_id})")
        elif payload.status == "error":
            logger.error(f"Webhook de erro recebido: job_id={payload.job_id}, error_type={payload.error_type}, error_message={payload.error_message}")
        return {"status": "ok"}
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        logger.error(f"Erro ao processar webhook MCP: {exc}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar webhook MCP.")
